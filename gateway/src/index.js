const { Client, LocalAuth, Poll } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const axios = require('axios');

const app = express();
app.use(express.json());

const BOT_URL = process.env.BOT_URL || 'http://localhost:8000';
const BOT_NAME = (process.env.BOT_NAME || 'Regelebot').toLowerCase();
const PORT = process.env.PORT || 3000;
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET;

// Support comma-separated chat IDs (groups + 1-to-1), with backward compat
const rawChatIds = process.env.WHATSAPP_CHAT_IDS || process.env.WHATSAPP_GROUP_ID || '';
const CHAT_IDS = new Set(rawChatIds.split(',').map(s => s.trim()).filter(Boolean));

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
        ],
    },
});

client.on('qr', (qr) => {
    console.log('');
    console.log('='.repeat(50));
    console.log('  Scannez ce QR code avec WhatsApp :');
    console.log('  (WhatsApp > Appareils lies > Lier un appareil)');
    console.log('='.repeat(50));
    console.log('');
    qrcode.generate(qr, { small: true });
});

client.on('authenticated', () => {
    console.log('[Gateway] Authentification reussie');
});

client.on('ready', () => {
    console.log('[Gateway] WhatsApp connecte et pret !');
    if (CHAT_IDS.size > 0) {
        console.log(`[Gateway] Chats actifs: ${[...CHAT_IDS].join(', ')}`);
    } else {
        console.log('[Gateway] WHATSAPP_CHAT_IDS non defini.');
        console.log('[Gateway] Envoyez un message dans un chat pour voir son ID dans les logs.');
    }
});

// Per-chat processing guard: prevents reply loops in 1-to-1 and self-chats.
// While handleMessage is running for a chat, any new message in that chat is skipped.
const processing = new Set();

// Handle incoming messages
async function handleMessage(message, eventName) {
    const body = message.body || '';

    // Get chat info to reliably identify the group
    let chat;
    try {
        chat = await message.getChat();
    } catch (e) {
        return;
    }

    const chatId = chat.id._serialized;

    // Discovery mode: log all chats when no IDs configured
    if (CHAT_IDS.size === 0) {
        console.log(`[Gateway][${eventName}] chat=${chatId} isGroup=${chat.isGroup} chatName="${chat.name}" fromMe=${message.fromMe} body="${body.substring(0, 50)}"`);
        console.log(`[Gateway] *** CHAT DETECTE: ${chatId} (${chat.isGroup ? 'groupe' : '1-to-1'}) ***`);
        if (chat.name) console.log(`[Gateway] *** Nom: ${chat.name} ***`);
        console.log(`[Gateway] → Ajoutez WHATSAPP_CHAT_IDS=${chatId} dans votre .env`);
        return;
    }

    // Filter: only configured chats
    if (!CHAT_IDS.has(chatId)) return;

    // Skip if already processing a message in this chat (prevents reply loops)
    if (processing.has(chatId)) return;

    const isDirect = !chat.isGroup;

    // In group chats, require a command or @mention; in 1-to-1, respond to everything
    if (!isDirect) {
        const isCommand = body.startsWith('/');
        const lower = body.toLowerCase();
        const isMention = lower.includes(`@${BOT_NAME}`) || lower.includes('@regelebot');
        if (!isCommand && !isMention) return;
    }

    processing.add(chatId);
    try {
        // Show typing indicator
        await chat.sendStateTyping();

        // Get sender name
        let senderName = 'Membre';
        try {
            const contact = await message.getContact();
            senderName = contact.pushname || contact.name || 'Membre';
        } catch (e) {
            // fromMe messages may not have a resolvable contact
            if (client.info && client.info.pushname) {
                senderName = client.info.pushname;
            }
        }

        console.log(`[Gateway] Processing: ${senderName}: ${body.substring(0, 80)}`);

        // Send to Python bot
        const response = await axios.post(`${BOT_URL}/webhook/message`, {
            from_: chatId,
            sender: message.author || message.from,
            sender_name: senderName,
            body: body,
            timestamp: message.timestamp,
            is_direct: isDirect,
        }, {
            timeout: 30000,
            headers: { 'X-Webhook-Secret': WEBHOOK_SECRET },
        });

        // Clear typing indicator
        await chat.clearState();

        // Send native WhatsApp poll if present, otherwise reply with text
        if (response.data && response.data.poll) {
            const poll = new Poll(
                response.data.poll.question,
                response.data.poll.options,
                { allowMultipleAnswers: false }
            );
            const sentMsg = await chat.sendMessage(poll);
            // Mark as handled so dedup ignores the bot's own message
            if (sentMsg && sentMsg.id) handled.add(sentMsg.id._serialized);
            // Link WhatsApp message to DB poll
            if (response.data.poll.poll_id && sentMsg && sentMsg.id) {
                try {
                    await axios.post(`${BOT_URL}/webhook/poll-created`, {
                        poll_id: response.data.poll.poll_id,
                        wa_message_id: sentMsg.id._serialized,
                    }, {
                        headers: { 'X-Webhook-Secret': WEBHOOK_SECRET },
                    });
                    console.log(`[Gateway] Linked poll ${response.data.poll.poll_id} to WA msg ${sentMsg.id._serialized}`);
                } catch (linkErr) {
                    console.error(`[Gateway] Failed to link poll: ${linkErr.message}`);
                }
            }
        } else if (response.data && response.data.reply) {
            // Reply to the original message so it's clear the bot is responding
            const sentReply = await message.reply(response.data.reply);
            // Mark as handled so dedup ignores the bot's own reply
            if (sentReply && sentReply.id) handled.add(sentReply.id._serialized);
        }
    } catch (error) {
        console.error(`[Gateway] Erreur: ${error.message}`);
        if (error.code === 'ECONNREFUSED') {
            console.error('[Gateway] Bot Python non accessible.');
        }
    } finally {
        processing.delete(chatId);
    }
}

// Listen on both events
// 'message' fires for incoming messages from others
// 'message_create' fires for all messages including own — needed because
// in some WhatsApp versions, group messages only come through message_create
const handled = new Set();

function dedup(msg, eventName) {
    const key = `${msg.id._serialized}`;
    if (handled.has(key)) return;
    handled.add(key);
    // Prevent memory leak: cap at 1000 entries
    if (handled.size > 1000) {
        const first = handled.values().next().value;
        handled.delete(first);
    }
    handleMessage(msg, eventName);
}

client.on('message', (msg) => dedup(msg, 'message'));
client.on('message_create', (msg) => dedup(msg, 'message_create'));

// Listen for native WhatsApp poll votes
client.on('vote_update', async (vote) => {
    try {
        const selectedOptions = vote.selectedOptions.map(o => o.name).filter(Boolean);
        if (selectedOptions.length === 0) return;

        const parentMsg = vote.parentMessage;
        if (!parentMsg || !parentMsg.id) return;

        // Resolve voter contact name
        let voterName = 'Membre';
        try {
            const contact = await client.getContactById(vote.voter);
            voterName = contact?.pushname || contact?.name || 'Membre';
        } catch (e) {
            // fallback to voter ID
        }

        await axios.post(`${BOT_URL}/webhook/poll-vote`, {
            wa_message_id: parentMsg.id._serialized,
            voter: vote.voter,
            voter_name: voterName,
            selected_options: selectedOptions,
        }, {
            headers: { 'X-Webhook-Secret': WEBHOOK_SECRET },
        });
        console.log(`[Gateway] Poll vote forwarded: ${voterName} -> ${selectedOptions.join(', ')}`);
    } catch (err) {
        console.error('[Gateway] vote_update error:', err.message);
    }
});

client.on('disconnected', (reason) => {
    console.log(`[Gateway] Deconnecte: ${reason}`);
    console.log('[Gateway] Tentative de reconnexion...');
    client.initialize();
});

// Health check endpoint
app.get('/health', (req, res) => {
    const info = client.info;
    res.json({
        status: info ? 'connected' : 'disconnected',
    });
});

// Start
client.initialize();
app.listen(PORT, () => {
    console.log(`[Gateway] Health check sur port ${PORT}`);
    console.log(`[Gateway] Bot URL: ${BOT_URL}`);
});
