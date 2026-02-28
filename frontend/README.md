# Frontend — React Website
### Person D works in this folder

---

## Setup

```
cd frontend
npm install
npm start       ← opens at localhost:3000
```

---

## The 4 screens

| Screen | File | What it shows |
|--------|------|---------------|
| 1. Upload | `src/components/Upload.js` | File picker. "Upload & Start Quiz" button. |
| 2. Quiz | `src/components/Quiz.js` | 5 questions with A/B/C radio buttons. Submit. |
| 3. Level Result | `src/components/LevelResult.js` | Score, detected level, level override buttons, "Transform" button. |
| 4. Download | `src/components/Download.js` | Download link for the personalized document. |

---

## How the screens connect (in App.js)

```
Upload  →  onDone(filename, questions)   →  Quiz screen
Quiz    →  onDone(quizResult)            →  Level Result screen
Level   →  onTransform(downloadData)    →  Download screen
Download →  onReset()                   →  back to Upload
```

---

## Plugging in the Lambda URLs (IMPORTANT)

Until Person A shares the Lambda URLs, the app won't connect to the backend.
Once you have the URLs, open `src/api.js` and replace the 4 placeholder strings.

---

## Build and send to Person A

```
npm run build
```

Send the entire `/build` folder to Person A. They upload it to S3 and the app goes live.
