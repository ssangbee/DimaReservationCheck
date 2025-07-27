const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const { spawn } = require('child_process');

const app = express();
const PORT = 8085;
const DATABASE_NAME = 'reservations.db';

// Serve static files from templates directory
app.use(express.static(path.join(__dirname, 'templates')));

// Initialize database
function initDB() {
    const db = new sqlite3.Database(DATABASE_NAME);
    db.run(`
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            room_name TEXT NOT NULL,
            student_id TEXT,
            student_name TEXT,
            reservation_date TEXT NOT NULL,
            reservation_time_slot TEXT NOT NULL,
            original_title TEXT NOT NULL,
            crawled_at TEXT NOT NULL
        )
    `, (err) => {
        if (err) {
            console.error('Error creating table:', err);
        } else {
            console.log('Database initialized successfully');
        }
    });
    db.close();
}

// Routes
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'templates', 'index.html'));
});

app.get('/api/reservations', (req, res) => {
    const selectedDate = req.query.date || new Date().toISOString().split('T')[0];
    const selectedCategory = req.query.category || 'all';

    const db = new sqlite3.Database(DATABASE_NAME);

    let query = `SELECT category, room_name, student_id, student_name, reservation_date,
                        reservation_time_slot, original_title, crawled_at
                 FROM reservations WHERE reservation_date = ?`;
    let params = [selectedDate];

    if (selectedCategory !== 'all') {
        query += ' AND category LIKE ?';
        params.push(`%${selectedCategory}%`);
    }

    query += ' ORDER BY room_name, reservation_time_slot';

    db.all(query, params, (err, rows) => {
        if (err) {
            console.error('Database error:', err);
            res.status(500).json({ error: 'Database error' });
        } else {
            res.json(rows);
        }
    });

    db.close();
});

app.get('/api/refresh_data', (req, res) => {
    const selectedDate = req.query.date;
    const selectedCategory = req.query.category;

    const command = ['python3', 'scrape_daum_cafe.py'];
    if (selectedDate) command.push(selectedDate);
    if (selectedCategory) command.push(selectedCategory);

    // Note: This will fail if Python dependencies aren't available
    // For now, just return a placeholder response
    console.log('Would run:', command.join(' '));
    res.json({ status: 'refresh started (placeholder - Python scraper not available)' });
});

// Initialize database and start server
initDB();

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
