import React, { useState } from 'react'
import axios from 'axios'

export default function Home() {
  const [file, setFile] = useState(null)
  const [job, setJob] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    fd.append('job_description', job)
    try {
      setLoading(true)
      const resp = await axios.post('http://localhost:8000/api/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResult(resp.data)
    } catch (err) {
      setResult({ error: err.response?.data || err.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: 24 }}>
      <h1>AI Resume Screening — Upload</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Resume (PDF):</label>
          <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files[0])} />
        </div>
        <div style={{ marginTop: 12 }}>
          <label>Job description:</label>
          <br />
          <textarea rows={8} cols={80} value={job} onChange={(e) => setJob(e.target.value)} />
        </div>
        <div style={{ marginTop: 12 }}>
          <button type="submit" disabled={loading}>{loading ? 'Processing...' : 'Upload'}</button>
        </div>
      </form>
      <pre style={{ marginTop: 12 }}>{result ? JSON.stringify(result, null, 2) : 'No result yet'}</pre>
    </div>
  )
}
