import React from 'react';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import Features from './components/Features';
import EndpointAgent from './components/EndpointAgent';
import MultiTenant from './components/MultiTenant';
import DashboardPreview from './components/DashboardPreview';
import Footer from './components/Footer';
import Pricing from './components/Pricing';

function App() {
  return (
    <div className="app">
      <Navbar />
      <main>
        <Hero />
        <Features />
        <EndpointAgent />
        <MultiTenant />
        <DashboardPreview />
        <Pricing />
        <section style={{ textAlign: 'center', padding: '10rem 0' }}>
          <div className="container">
            <h2 style={{ fontSize: '3.5rem', marginBottom: '1.5rem' }}>Ready to <span className="grad-text">Secure</span> Your Tenants?</h2>
            <p style={{ fontSize: '1.25rem', marginBottom: '3rem' }}>Join the security teams who power their posture with SpecterDefence.</p>
            <button className="btn-primary grad-bg" style={{ fontSize: '1.25rem', padding: '1.25rem 3rem', borderRadius: '16px', color: 'white' }}>
              Get Started for Free
            </button>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}

export default App;
