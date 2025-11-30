export default function Privacy(){
  return (
    <div className="container">
      <h1>Privacy Policy</h1>
      <p>Last updated: {new Date().toISOString().slice(0,10)}</p>
      <p>We only collect the minimum information required to provide AQI alerts (email, optional phone). We do not sell personal data. We use third-party services for hosting, analytics, and ads (Vercel, Render, Google Analytics, Google AdSense).</p>
      <h2>Data sources</h2>
      <p>Air quality data is aggregated from public APIs (CPCB, OpenAQ, WAQI/IQAir when configured).</p>
      <h2>Contact</h2>
      <p>For data/deletion requests: contact@aqiindia.live</p>
    </div>
  )
}
