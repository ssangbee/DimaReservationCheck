
from flask import Flask, jsonify, render_template, request
import sqlite3
import datetime
import subprocess

app = Flask(__name__)
DATABASE_NAME = 'reservations.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # This allows access to columns by name
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/reservations')
def get_reservations():
    conn = get_db_connection()
    selected_date_str = request.args.get('date', datetime.date.today().strftime('%Y-%m-%d'))
    selected_category = request.args.get('category', 'all')

    query = 'SELECT category, room_name, student_id, student_name, reservation_date, reservation_time_slot, original_title, crawled_at, crawled_day_of_week FROM reservations WHERE reservation_date = ?'
    params = [selected_date_str]

    if selected_category != 'all':
        # Adjust category names to match what's stored in the DB if necessary
        # Assuming '일반 연습실' and '스튜디오/랩/라운지' are the exact category names in the DB
        query += ' AND category LIKE ?'
        params.append(f'%{selected_category}%')

    query += ' ORDER BY room_name, reservation_time_slot'
    reservations = conn.execute(query, tuple(params)).fetchall()
    conn.close()

    # Convert rows to a list of dictionaries
    reservations_list = []
    for row in reservations:
        reservations_list.append(dict(row))
    
    return jsonify(reservations_list)

@app.route('/api/refresh_data')
def refresh_data():
    selected_date = request.args.get('date')
    selected_category = request.args.get('category')

    command = ["python3", "scrape_daum_cafe.py"]
    if selected_date:
        command.append(selected_date)
    if selected_category:
        command.append(selected_category)

    # Run the scraping script synchronously and wait for it to complete.
    try:
        # Using subprocess.run makes this a blocking call.
        # The API will not return until the script is finished.
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=300) # 5-minute timeout
        with open('app.log', 'a') as f:
            f.write(f"""Scrape for {selected_date} ({selected_category}) completed successfully.""" + '\n')
            f.write(result.stdout + '\n')
        return jsonify({"status": "refresh completed"})
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        error_message = e.stderr if hasattr(e, 'stderr') else str(e)
        with open('app.log', 'a') as f:
            f.write(f"""Scrape for {selected_date} ({selected_category}) failed: {error_message}""" + '\n')
        return jsonify({"status": "refresh failed", "error": error_message}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8082)
