# SparkLabs Official Website

The official website for SparkLabs AI-Native Game Engine.

## Deployment

### Local Development

```bash
cd frontend/website
npm install
npm run dev
```

The website runs at `http://localhost:8080`.

### Static Hosting

The website consists of static HTML files (`index.html`, `editor.html`, `sparklabs.html`) that can be deployed to any static hosting service:

- **GitHub Pages** — Push the `frontend/website/` directory
- **Vercel** — Connect the repository and set the root to `frontend/website/`
- **Netlify** — Set the publish directory to `frontend/website/`
- **AWS S3 + CloudFront** — Upload files to S3 bucket with static hosting enabled

### Production Build

No build step required. The website is pre-built static HTML with inline styles and CDN-hosted dependencies.

## Features

| Feature | Description |
|---------|-------------|
| Landing Page | Hero section with AI engine showcase |
| Feature Sections | Core capabilities, engine architecture, game showcase |
| Waitlist | Email signup form for early access |
| Testimonials | Creator testimonials and case studies |
| Responsive | Full responsive design for mobile and desktop |

## Isolation from Editor

The official website and the SparkLabs Editor are completely independent:

- **Website** runs on port 8080 (static HTML, no build step)
- **Editor** runs on port 3000 (React + Vite, requires build)
- They share no runtime dependencies or state
- Each can be deployed, started, and stopped independently
- The website does not require the backend API
- The editor can function in standalone mode without the backend

## File Structure

```
frontend/website/
├── index.html        # Main landing page
├── editor.html       # Legacy editor preview page
├── sparklabs.html    # SparkLabs product page
├── package.json      # Development server config
└── README.md         # This file
```
