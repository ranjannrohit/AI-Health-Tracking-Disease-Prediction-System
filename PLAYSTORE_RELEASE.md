# HealthTrackk Play Store Release Guide

This project now includes:

- Capacitor Android project in `android/`
- Mobile shell in `www/`
- App package ID: `com.rohit.healthtrackk`

## Important reality check

To publish on Google Play, the app must load a real production HealthTrackk experience.

Right now the Android shell is ready, but you still need to:

1. Deploy HealthTrackk to a public HTTPS domain.
2. Put that URL in `www/mobile-config.js`.
3. Sync Capacitor assets into Android.
4. Build a signed release AAB.

## 1. Set your production URL

Edit:

`www/mobile-config.js`

Replace:

`https://your-healthtrackk-domain.example`

with your real deployed URL, for example:

`https://app.healthtrackk.com`

## 2. Sync the app

Run from project root:

```powershell
npm run cap:copy
npm run cap:sync
```

If PowerShell blocks npm scripts on your machine, use:

```powershell
node node_modules/@capacitor/cli/bin/capacitor copy
node node_modules/@capacitor/cli/bin/capacitor sync
```

## 3. Open Android Studio

```powershell
npm run cap:open:android
```

Or:

```powershell
node node_modules/@capacitor/cli/bin/capacitor open android
```

## 4. Build release bundle

In Android Studio:

1. Let Gradle sync.
2. Set your signing config.
3. Build `Generate Signed Bundle / APK`.
4. Choose `Android App Bundle (AAB)`.

## 5. Play Store checklist

Before submission, prepare:

- App icon
- Feature graphic
- Phone screenshots
- Privacy policy URL
- Data safety form
- Content rating
- App access instructions if login is required
- Support email

## 6. Recommended production improvements

Before store submission, I recommend:

- Replace placeholder mobile URL in `www/mobile-config.js`
- Add real app icons in Android mipmap resources
- Turn on release shrinking/optimization if stable
- Add privacy policy page on your production domain
- Test login, OTP, chatbot, dashboard, location, and nearby hospitals on a physical Android device

## 7. Store review risk

If the app is only a thin wrapper around a website, Google may reject it for low added value.

To reduce that risk, make sure the mobile app experience includes:

- polished onboarding
- stable authentication
- reliable mobile navigation
- fast loading
- mobile-specific permissions and flows
- clear value beyond just opening a webpage
