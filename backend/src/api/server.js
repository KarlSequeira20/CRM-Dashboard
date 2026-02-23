import express from 'express';
import cors from 'cors';
import { supabase } from '../utils/supabaseClient.js';
import aiRoutes from './aiRoutes.js';

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Main health-check and routing
app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date() });
});

// Load feature routes
app.use('/api/ai', aiRoutes);

app.listen(PORT, () => {
    console.log(`[API Server] Running on http://localhost:${PORT}`);
});
