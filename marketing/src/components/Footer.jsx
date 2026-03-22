import React from 'react';
import { Shield, Github, Twitter, Linkedin, Mail } from 'lucide-react';

const Footer = () => {
  return (
    <footer style={{ padding: '6rem 0 3rem', background: 'var(--bg-dark)', borderTop: '1px solid var(--glass-border)' }}>
      <div className="container">
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: '4rem', marginBottom: '4rem' }}>
          <div>
            <div className="flex-center" style={{ justifyContent: 'flex-start', gap: '0.75rem', marginBottom: '1.5rem' }}>
              <Shield className="grad-text" size={32} />
              <span style={{ fontWeight: 800, fontSize: '1.5rem', letterSpacing: '-0.5px' }}>
                Specter<span className="grad-text">Defence</span>
              </span>
            </div>
            <p style={{ maxWidth: '300px', fontSize: '1rem' }}>
              Advanced Microsoft 365 security posture monitoring and real-time threat detection for the modern enterprise.
            </p>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
              <Github className="hover-white" size={20} style={{ cursor: 'pointer', color: 'var(--text-muted)' }} />
              <Twitter className="hover-white" size={20} style={{ cursor: 'pointer', color: 'var(--text-muted)' }} />
              <Linkedin className="hover-white" size={20} style={{ cursor: 'pointer', color: 'var(--text-muted)' }} />
            </div>
          </div>

          <div>
            <h4 style={{ marginBottom: '1.5rem' }}>Product</h4>
            <ul style={{ listStyle: 'none', space: '0.75rem', color: 'var(--text-muted)' }}>
              <li><a href="#features" className="hover-white" style={{ display: 'block', marginBottom: '0.5rem' }}>Features</a></li>
              <li><a href="#endpoint" className="hover-white" style={{ display: 'block', marginBottom: '0.5rem' }}>Endpoint Agent</a></li>
              <li><a href="#dashboard" className="hover-white" style={{ display: 'block', marginBottom: '0.5rem' }}>Dashboard</a></li>
              <li><a href="#api" className="hover-white" style={{ display: 'block', marginBottom: '0.5rem' }}>API Reference</a></li>
            </ul>
          </div>

          <div>
            <h4 style={{ marginBottom: '1.5rem' }}>Company</h4>
            <ul style={{ listStyle: 'none', space: '0.75rem', color: 'var(--text-muted)' }}>
              <li><a href="#" className="hover-white" style={{ display: 'block', marginBottom: '0.5rem' }}>About Us</a></li>
              <li><a href="#" className="hover-white" style={{ display: 'block', marginBottom: '0.5rem' }}>Blog</a></li>
              <li><a href="#" className="hover-white" style={{ display: 'block', marginBottom: '0.5rem' }}>Careers</a></li>
              <li><a href="#" className="hover-white" style={{ display: 'block', marginBottom: '0.5rem' }}>Status</a></li>
            </ul>
          </div>

          <div>
            <h4 style={{ marginBottom: '1.5rem' }}>Legal</h4>
            <ul style={{ listStyle: 'none', space: '0.75rem', color: 'var(--text-muted)' }}>
              <li><a href="#" className="hover-white" style={{ display: 'block', marginBottom: '0.5rem' }}>Privacy Policy</a></li>
              <li><a href="#" className="hover-white" style={{ display: 'block', marginBottom: '0.5rem' }}>Terms of Service</a></li>
              <li><a href="#" className="hover-white" style={{ display: 'block', marginBottom: '0.5rem' }}>Security</a></li>
              <li><a href="#" className="hover-white" style={{ display: 'block', marginBottom: '0.5rem' }}>SLA</a></li>
            </ul>
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--glass-border)', paddingTop: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          <p>© 2026 SpecterDefence. All rights reserved.</p>
          <div style={{ display: 'flex', gap: '2rem' }}>
            <span>Built with ❤️ for Security Teams</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
