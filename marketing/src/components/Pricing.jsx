import React from 'react';
import { Check, Shield, Zap, Globe, Cloud, Server } from 'lucide-react';

const PricingCard = ({ title, price, features, highlighted, icon: Icon, subtitle, type }) => (
  <div className={`glass glass-card ${highlighted ? 'grad-border' : ''}`} style={{
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    position: 'relative',
    overflow: 'hidden',
    zIndex: 1
  }}>
    {highlighted && (
      <div className="grad-bg" style={{
        position: 'absolute',
        top: '1rem',
        right: '-2rem',
        transform: 'rotate(45deg)',
        padding: '0.25rem 3rem',
        fontSize: '0.75rem',
        fontWeight: 'bold',
        color: 'white'
      }}>
        POPULAR
      </div>
    )}
    
    <div style={{ marginBottom: '2rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
        <span className="glass-pill" style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', background: type === 'hosted' ? 'rgba(0, 242, 254, 0.1)' : 'rgba(255, 255, 255, 0.05)', color: type === 'hosted' ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
          {type === 'hosted' ? 'Hosted' : 'Self-Hosted'}
        </span>
      </div>
      <div className="flex-center" style={{ 
        width: '3.5rem', 
        height: '3.5rem', 
        borderRadius: '16px', 
        background: 'rgba(255, 255, 255, 0.03)',
        marginBottom: '1.5rem',
        color: highlighted ? 'var(--accent-cyan)' : 'white',
        border: '1px solid var(--glass-border)'
      }}>
        <Icon size={28} />
      </div>
      <h3 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '0.25rem' }}>{title}</h3>
      <p style={{ fontSize: '0.9rem', marginBottom: '1.5rem', color: 'var(--text-muted)' }}>{subtitle}</p>
      
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem' }}>
        <span style={{ fontSize: '2.5rem', fontWeight: 800 }}>{price}</span>
        {price !== 'Custom' && <span style={{ color: 'var(--text-muted)' }}>/mo</span>}
      </div>
    </div>

    <div style={{ flex: 1 }}>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {features.map((feature, i) => (
          <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.95rem' }}>
            <Check size={18} className="grad-text" style={{ flexShrink: 0 }} />
            <span style={{ color: 'var(--text-muted)' }}>{feature}</span>
          </li>
        ))}
      </ul>
    </div>

    <button className={highlighted ? 'btn-primary grad-bg glow-hov' : 'btn-outline'} style={{ 
      width: '100%', 
      marginTop: '2.5rem',
      color: highlighted ? 'white' : 'inherit',
      padding: '1.25rem'
    }}>
      {price === 'Custom' ? 'Contact Sales' : 'Get Started'}
    </button>
  </div>
);

const Pricing = () => {
  const tiers = [
    {
      title: 'Community',
      subtitle: 'Free forever for individuals.',
      price: '$0',
      type: 'self-hosted',
      icon: Server,
      features: [
        'Up to 3 Managed Tenants',
        'Basic Security Analytics',
        'Community Support',
        'Open Source Core'
      ]
    },
    {
      title: 'Professional',
      subtitle: 'Flat rate for growing MSPs.',
      price: '$49',
      type: 'self-hosted',
      icon: Zap,
      features: [
        'Unlimited Tenants',
        'Custom Security Rules',
        'API Access',
        'Email Support',
        'Advanced Analytics'
      ]
    },
    {
      title: 'Specter Cloud',
      subtitle: 'Zero-maintenance SaaS.',
      price: '$149',
      type: 'hosted',
      icon: Cloud,
      highlighted: true,
      features: [
        'Fully Managed Infrastructure',
        'Automated Daily Updates',
        'Zero Maintenance',
        'Priority Slack Support',
        'Daily Off-site Backups'
      ]
    },
    {
      title: 'Enterprise',
      subtitle: 'Scalable security for large orgs.',
      price: 'Custom',
      type: 'hosted',
      icon: Globe,
      features: [
        'Dedicated Cloud Instance',
        'White-label Reporting',
        'SSO & SAML Integration',
        '24/7 Dedicated Support',
        'Compliance Auditing (18mo+)'
      ]
    }
  ];

  return (
    <section id="pricing" className="container">
      <div style={{ textAlign: 'center', marginBottom: '5rem' }}>
        <h2 className="grad-text" style={{ display: 'inline-block', marginBottom: '1rem' }}>Simple, Transparent Pricing</h2>
        <p style={{ maxWidth: '600px', margin: '0 auto', fontSize: '1.25rem' }}>
          Predictable costs for teams of any size. Choose between self-hosted control or hosted simplicity.
        </p>
      </div>

      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', 
        gap: '1.5rem',
        alignItems: 'stretch'
      }}>
        {tiers.map((tier, i) => (
          <PricingCard key={i} {...tier} />
        ))}
      </div>

      <p style={{ textAlign: 'center', marginTop: '4rem', fontSize: '0.9rem' }}>
        Need a custom proof of concept? <a href="#" className="grad-text" style={{ fontWeight: 600 }}>Get in touch &rarr;</a>
      </p>
    </section>
  );
};

export default Pricing;
