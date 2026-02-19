# MatEl v1.0.1 - The "Identity" Update 🦅
**Release Date:** 2026-02-19

## 🚀 New Features
- **User Profiles**: Users can now personalize their account by adding a **Bio** and a **Custom Avatar URL**.
- **Account Recovery System**:
  - **Forgot Password**: Secure, token-based password reset flow via email.
  - **Forgot Username**: Retrieve your forgotten username directly to your registered email.
- **Enhanced Sidebar**: Now displays the user's specific **Role** (e.g., HEAD ADMIN, USER) and real-time Avatar.

## 🎨 UI/UX Enhancements
- **Login Page Redesign**: A complete visual overhaul featuring specific "Cyberpunk/Glassmorphism" aesthetics:
  - Animated glowing background orbs.
  - Frosted glass card effect.
  - Interactive "glow" states on input fields.
- **Visual Bug Fixes**: Fixed the misalignment of the lock/password icon in the login form.
- **Improved Feedback**: Better error and success messages during profile updates and form submissions.

## 🛠 Technical & Backend
- **Database Schema**: Migrated `users` table to include `bio`, `avatar_url`, and `reset_token`.
- **API Endpoints**:
  - `POST /api/auth/forgot-password`
  - `POST /api/auth/forgot-username`
  - `POST /api/auth/reset-password`
  - `PUT /api/auth/me/profile`
- **Email System**: Added HTML templates for password reset and username recovery emails.

---

