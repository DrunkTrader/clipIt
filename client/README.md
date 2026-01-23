# ClipIt - Twitter Video Clipper Client

A beautiful, minimalistic web app to download and clip Twitter/X videos.

## Features

✨ **Light & Cartoonish Design** - Inspired by Gumroad's clean aesthetic
🎬 **Full Video Download** - Get the entire video with one click
✂️ **Smart Clipping** - Create custom clips by specifying start and end times
💾 **One-Click Download** - Downloads directly to your chosen folder
🚀 **Fast & Responsive** - Built with Next.js and React

## Getting Started

### Prerequisites
- Node.js 18+ installed
- Running backend server (see server folder)

### Installation

1. Install dependencies:
```bash
npm install
```

2. Run the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser

## Usage

1. **Paste Video URL**: Copy any Twitter/X video URL and paste it
2. **Optional Clipping**: 
   - Leave time fields empty for full video download
   - Or enter start and end times for a specific clip
3. **Download**: Click the button and your video downloads instantly!

## Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:9000
```

## Tech Stack

- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Axios** - HTTP client

## Design Philosophy

The UI follows a light, minimalistic, and friendly design inspired by Gumroad:
- Soft pink accent colors
- Rounded corners and playful emojis
- Clean white cards on a warm background
- Smooth animations and transitions
- Clear call-to-action buttons

Enjoy clipping! ✂️🎬
