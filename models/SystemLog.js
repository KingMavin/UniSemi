const mongoose = require('mongoose');

const systemLogSchema = new mongoose.Schema({
  action: { type: String, required: true },
  details: String,
  timestamp: { type: Date, default: Date.now }
}, { timestamps: true });

module.exports = mongoose.model('SystemLog', systemLogSchema);

