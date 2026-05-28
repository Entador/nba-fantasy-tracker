// Single platform-specific point: web reads the Next.js public env var.
// On React Native this file is the one to swap (e.g. expo-constants).
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
