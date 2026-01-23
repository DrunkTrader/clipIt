import VideoClipperForm from '@/components/VideoClipperForm'

export default function Home() {
  return (
    <main className="min-h-screen py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-block mb-4">
            <div className="bg-white rounded-full p-4 shadow-lg border-4 border-pink-100">
              <svg 
                className="w-16 h-16 text-pink-500" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" 
                />
              </svg>
            </div>
          </div>
          <h1 className="text-5xl font-bold text-gray-900 mb-3">
            ClipIt ✂️
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Download Twitter/X videos instantly or create custom clips with just a few clicks
          </p>
        </div>

        {/* Main Form */}
        <VideoClipperForm />

        {/* Footer */}
        <footer className="text-center mt-16 pb-8">
          <p className="text-gray-500 text-sm">
            Made with ❤️ for content creators
          </p>
        </footer>
      </div>
    </main>
  )
}
