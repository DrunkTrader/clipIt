'use client'

import { useState } from 'react'
import axios from 'axios'

interface ClipResponse {
  download_link: string
}

export default function VideoClipperForm() {
  const [tweetUrl, setTweetUrl] = useState('')
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [downloadLink, setDownloadLink] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setDownloadLink('')

    try {
      // Validate inputs
      if (!tweetUrl) {
        throw new Error('Please enter a Twitter/X video URL')
      }

      // Build request body
      const requestBody: any = { tweet_url: tweetUrl }

      // Only include start and end if both are provided
      if (startTime && endTime) {
        const start = parseFloat(startTime)
        const end = parseFloat(endTime)

        if (isNaN(start) || isNaN(end)) {
          throw new Error('Start and end times must be valid numbers')
        }

        if (start < 0) {
          throw new Error('Start time must be 0 or greater')
        }

        if (end <= start) {
          throw new Error('End time must be greater than start time')
        }

        requestBody.start = start
        requestBody.end = end
      } else if (startTime || endTime) {
        throw new Error('Please provide both start and end times, or leave both empty for full video')
      }

      // Make API request
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9000'
      const response = await axios.post<ClipResponse>(`${apiUrl}/clip`, requestBody)

      setDownloadLink(response.data.download_link)
    } catch (err: any) {
      if (axios.isAxiosError(err)) {
        setError(
          err.response?.data?.detail || 
          err.message || 
          'An error occurred while processing your request'
        )
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('An unexpected error occurred')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = () => {
    // Create a temporary anchor element to trigger download
    const link = document.createElement('a')
    link.href = downloadLink
    link.download = '' // Browser will use the filename from the server
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const resetForm = () => {
    setTweetUrl('')
    setStartTime('')
    setEndTime('')
    setError('')
    setDownloadLink('')
  }

  return (
    <div className="bg-white rounded-3xl shadow-xl border-4 border-pink-100 overflow-hidden">
      {!downloadLink ? (
        <form onSubmit={handleSubmit} className="p-8">
          {/* URL Input */}
          <div className="mb-6">
            <label 
              htmlFor="tweetUrl" 
              className="block text-sm font-semibold text-gray-700 mb-2"
            >
              🔗 Twitter/X Video URL
            </label>
            <input
              type="url"
              id="tweetUrl"
              value={tweetUrl}
              onChange={(e) => setTweetUrl(e.target.value)}
              placeholder="https://twitter.com/username/status/123456789"
              className="w-full px-5 py-4 rounded-2xl bg-pink-50 border-2 border-pink-100 text-gray-800 placeholder-gray-400 focus:outline-none focus:border-pink-300 focus:bg-white text-lg"
              required
            />
          </div>

          {/* Time Inputs */}
          <div className="mb-6 p-6 bg-gray-50 rounded-2xl border-2 border-gray-100">
            <div className="mb-3 text-center">
              <span className="text-sm font-semibold text-gray-600">
                ✨ Want a specific clip? (Optional)
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label 
                  htmlFor="startTime" 
                  className="block text-sm font-medium text-gray-600 mb-2"
                >
                  ⏱️ Start (seconds)
                </label>
                <input
                  type="number"
                  id="startTime"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  placeholder="0"
                  step="0.1"
                  min="0"
                  className="w-full px-4 py-3 rounded-xl bg-white border-2 border-gray-200 text-gray-800 placeholder-gray-400 focus:outline-none focus:border-pink-300"
                />
              </div>

              <div>
                <label 
                  htmlFor="endTime" 
                  className="block text-sm font-medium text-gray-600 mb-2"
                >
                  ⏱️ End (seconds)
                </label>
                <input
                  type="number"
                  id="endTime"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  placeholder="10"
                  step="0.1"
                  min="0.1"
                  className="w-full px-4 py-3 rounded-xl bg-white border-2 border-gray-200 text-gray-800 placeholder-gray-400 focus:outline-none focus:border-pink-300"
                />
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-3 text-center">
              💡 Leave empty to download the full video
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 bg-red-50 border-2 border-red-200 rounded-2xl p-4">
              <div className="flex items-start">
                <span className="text-2xl mr-3">⚠️</span>
                <p className="text-red-700 text-sm font-medium">{error}</p>
              </div>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className={`w-full py-5 px-6 rounded-2xl font-bold text-white text-lg shadow-lg transition-all transform ${
              loading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-pink-500 to-pink-600 hover:from-pink-600 hover:to-pink-700 hover:shadow-xl hover:scale-[1.02] active:scale-[0.98]'
            }`}
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg
                  className="animate-spin -ml-1 mr-3 h-6 w-6 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Processing your video...
              </span>
            ) : (
              <>
                {startTime && endTime ? '✂️ Clip Video' : '⬇️ Download Video'}
              </>
            )}
          </button>
        </form>
      ) : (
        <div className="p-8 text-center">
          {/* Success Animation */}
          <div className="mb-6">
            <div className="inline-block bg-green-100 rounded-full p-6 mb-4 animate-bounce">
              <svg
                className="w-20 h-20 text-green-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={3}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h3 className="text-3xl font-bold text-gray-900 mb-2">
              Ready to Download! 🎉
            </h3>
            <p className="text-gray-600 text-lg">
              Your video is processed and ready
            </p>
          </div>

          {/* Download Button */}
          <button
            onClick={handleDownload}
            className="w-full mb-4 py-5 px-6 rounded-2xl font-bold text-white text-lg bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 shadow-lg hover:shadow-xl transform hover:scale-[1.02] active:scale-[0.98] transition-all"
          >
            💾 Download Now
          </button>

          {/* Preview/Open Link */}
          <a
            href={downloadLink}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full mb-4 py-4 px-6 rounded-2xl font-semibold text-pink-600 bg-pink-50 border-2 border-pink-200 hover:bg-pink-100 transition-all"
          >
            👁️ Preview Video
          </a>

          {/* Reset Button */}
          <button
            onClick={resetForm}
            className="w-full py-4 px-6 rounded-2xl font-semibold text-gray-700 bg-gray-100 border-2 border-gray-200 hover:bg-gray-200 transition-all"
          >
            ← Create Another Clip
          </button>

          {/* Info Box */}
          <div className="mt-6 p-4 bg-blue-50 border-2 border-blue-100 rounded-2xl">
            <p className="text-sm text-blue-700">
              💡 Tip: The download will save to your browser&apos;s default download folder. 
              You can change this in your browser settings.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
