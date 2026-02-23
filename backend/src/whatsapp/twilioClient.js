import twilio from 'twilio';
import { config } from '../config/env.js';

export async function sendWhatsAppMessage(messageText) {
    const { accountSid, authToken, fromNumber, toNumber } = config.twilio;

    if (!accountSid || !authToken || !toNumber) {
        console.warn("[Twilio] Credentials missing. Mocking WhatsApp Delivery. Simulated Output:\n");
        console.log("----------------------------------");
        console.log(messageText);
        console.log("----------------------------------");
        return;
    }

    const client = twilio(accountSid, authToken);

    try {
        const message = await client.messages.create({
            body: messageText,
            from: fromNumber,
            to: toNumber
        });
        console.log(`[Twilio] Message sent successfully! SID: ${message.sid}`);
    } catch (error) {
        console.error('[Twilio] Failed to send WhatsApp message:', error);
    }
}
