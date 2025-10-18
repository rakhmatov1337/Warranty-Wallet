/**
 * Frontend Integration Example for AI Analytics
 * This shows how to integrate the AI insights endpoint in your React/Vue/Angular app
 */

// ==================== React Example ====================

import React, { useState, useEffect } from 'react';
import axios from 'axios';

const AIInsightsDashboard = () => {
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [period, setPeriod] = useState('6months');

  useEffect(() => {
    fetchAIInsights();
  }, [period]);

  const fetchAIInsights = async () => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token'); // Your JWT token
      
      const response = await axios.get(
        `http://localhost:8000/api/analytics/ai-insights/`,
        {
          params: { period },
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      setInsights(response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to fetch insights');
      console.error('Error fetching AI insights:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading AI insights...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <div className="ai-insights-dashboard">
      <h1>AI-Powered Insights</h1>

      {/* Period Selector */}
      <div className="period-selector">
        <select value={period} onChange={(e) => setPeriod(e.target.value)}>
          <option value="30days">Last 30 Days</option>
          <option value="90days">Last 90 Days</option>
          <option value="6months">Last 6 Months</option>
          <option value="12months">Last 12 Months</option>
          <option value="all">All Time</option>
        </select>
      </div>

      {/* Overall Statistics */}
      <div className="stats-grid">
        <StatCard
          title="Total Claims"
          value={insights?.overall_statistics?.total_claims}
          color="blue"
        />
        <StatCard
          title="Approval Rate"
          value={`${insights?.overall_statistics?.approval_rate}%`}
          color="green"
        />
        <StatCard
          title="Pending Claims"
          value={insights?.overall_statistics?.pending_claims}
          color="orange"
        />
        <StatCard
          title="Rejection Rate"
          value={`${insights?.overall_statistics?.rejection_rate}%`}
          color="red"
        />
      </div>

      {/* AI Summary */}
      <div className="ai-summary">
        <h2>🤖 AI Summary</h2>
        <p>{insights?.ai_summary}</p>
        {insights?.claim_reasons?.ai_powered && (
          <span className="badge">✨ AI-Powered Analysis</span>
        )}
      </div>

      {/* Top Claimed Products */}
      <div className="top-products">
        <h2>🏆 Top Claimed Products</h2>
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Model</th>
              <th>Claims</th>
              <th>Approval Rate</th>
            </tr>
          </thead>
          <tbody>
            {insights?.top_claimed_products?.slice(0, 5).map((product, idx) => (
              <tr key={idx}>
                <td>{product.product_name}</td>
                <td>{product.model}</td>
                <td>{product.claim_count}</td>
                <td>
                  <span className={`rate ${product.approval_rate > 70 ? 'good' : 'warning'}`}>
                    {product.approval_rate}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Claim Reasons Chart */}
      <div className="claim-reasons">
        <h2>📊 Claim Reasons (AI Categorized)</h2>
        <div className="chart">
          {insights?.claim_reasons?.categories?.slice(0, 5).map((category, idx) => (
            <div key={idx} className="chart-bar">
              <span className="label">{category.category}</span>
              <div className="bar-container">
                <div
                  className="bar"
                  style={{ width: `${category.percentage}%` }}
                />
                <span className="value">{category.percentage}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recommendations */}
      <div className="recommendations">
        <h2>📋 Recommendations</h2>
        {insights?.recommendations?.map((rec, idx) => (
          <div key={idx} className={`recommendation ${rec.priority}`}>
            <div className="rec-header">
              <span className="priority-badge">{rec.priority}</span>
              <h3>{rec.title}</h3>
            </div>
            <p>{rec.description}</p>
            <div className="action">
              <strong>Action:</strong> {rec.action}
            </div>
          </div>
        ))}
      </div>

      {/* Slow Processing */}
      <div className="slow-processing">
        <h2>⏱️ Slow Processing Times</h2>
        <ul>
          {insights?.slow_processing_claims?.slice(0, 5).map((item, idx) => (
            <li key={idx}>
              <strong>{item.product_name}</strong>
              <span className="days">{item.avg_processing_days} days average</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

// Simple stat card component
const StatCard = ({ title, value, color }) => (
  <div className={`stat-card ${color}`}>
    <h3>{title}</h3>
    <div className="value">{value}</div>
  </div>
);

export default AIInsightsDashboard;


// ==================== Vue Example ====================

/*
<template>
  <div class="ai-insights-dashboard">
    <h1>AI-Powered Insights</h1>

    <select v-model="period" @change="fetchInsights">
      <option value="30days">Last 30 Days</option>
      <option value="90days">Last 90 Days</option>
      <option value="6months">Last 6 Months</option>
      <option value="12months">Last 12 Months</option>
      <option value="all">All Time</option>
    </select>

    <div v-if="loading">Loading...</div>
    <div v-else-if="error">{{ error }}</div>
    <div v-else>
      <!-- Display insights data here -->
      <div class="ai-summary">
        <h2>AI Summary</h2>
        <p>{{ insights.ai_summary }}</p>
      </div>

      <div class="stats">
        <div>Total Claims: {{ insights.overall_statistics.total_claims }}</div>
        <div>Approval Rate: {{ insights.overall_statistics.approval_rate }}%</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      insights: null,
      loading: true,
      error: null,
      period: '6months'
    };
  },
  mounted() {
    this.fetchInsights();
  },
  methods: {
    async fetchInsights() {
      this.loading = true;
      this.error = null;

      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(
          `http://localhost:8000/api/analytics/ai-insights/?period=${this.period}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );

        if (!response.ok) throw new Error('Failed to fetch insights');
        
        this.insights = await response.json();
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>
*/


// ==================== Plain JavaScript (Fetch API) ====================

async function getAIInsights(period = '6months') {
  const token = localStorage.getItem('access_token');
  
  try {
    const response = await fetch(
      `http://localhost:8000/api/analytics/ai-insights/?period=${period}`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log('AI Insights:', data);
    
    // Display the data
    displayInsights(data);
    
    return data;
  } catch (error) {
    console.error('Error fetching AI insights:', error);
    throw error;
  }
}

function displayInsights(insights) {
  // Overall stats
  document.getElementById('total-claims').textContent = 
    insights.overall_statistics.total_claims;
  document.getElementById('approval-rate').textContent = 
    `${insights.overall_statistics.approval_rate}%`;
  
  // AI Summary
  document.getElementById('ai-summary').textContent = insights.ai_summary;
  
  // Top products
  const productsTable = document.getElementById('top-products-table');
  productsTable.innerHTML = insights.top_claimed_products
    .slice(0, 5)
    .map(product => `
      <tr>
        <td>${product.product_name}</td>
        <td>${product.model}</td>
        <td>${product.claim_count}</td>
        <td>${product.approval_rate}%</td>
      </tr>
    `).join('');
  
  // Recommendations
  const recContainer = document.getElementById('recommendations');
  recContainer.innerHTML = insights.recommendations
    .map(rec => `
      <div class="recommendation ${rec.priority}">
        <h3>${rec.title}</h3>
        <p>${rec.description}</p>
        <strong>Action:</strong> ${rec.action}
      </div>
    `).join('');
}

// Usage
// getAIInsights('6months');


// ==================== CSS Example ====================

const exampleCSS = `
/* AI Insights Dashboard Styles */

.ai-insights-dashboard {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin: 20px 0;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stat-card.blue { border-left: 4px solid #3b82f6; }
.stat-card.green { border-left: 4px solid #10b981; }
.stat-card.orange { border-left: 4px solid #f59e0b; }
.stat-card.red { border-left: 4px solid #ef4444; }

.stat-card h3 {
  font-size: 14px;
  color: #6b7280;
  margin: 0 0 10px 0;
}

.stat-card .value {
  font-size: 32px;
  font-weight: bold;
  color: #1f2937;
}

.ai-summary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 30px;
  border-radius: 12px;
  margin: 20px 0;
}

.ai-summary h2 {
  margin-top: 0;
}

.badge {
  display: inline-block;
  background: rgba(255,255,255,0.2);
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  margin-top: 10px;
}

.top-products table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}

.top-products th,
.top-products td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.top-products th {
  background: #f9fafb;
  font-weight: 600;
}

.rate.good { color: #10b981; }
.rate.warning { color: #f59e0b; }

.claim-reasons {
  margin: 30px 0;
}

.chart-bar {
  margin: 15px 0;
}

.chart-bar .label {
  display: inline-block;
  width: 200px;
  font-weight: 500;
}

.bar-container {
  display: inline-block;
  width: calc(100% - 220px);
  position: relative;
}

.bar {
  height: 30px;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.bar-container .value {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-weight: 600;
}

.recommendation {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin: 15px 0;
  border-left: 4px solid #6b7280;
}

.recommendation.high {
  border-left-color: #ef4444;
  background: #fef2f2;
}

.recommendation.medium {
  border-left-color: #f59e0b;
  background: #fffbeb;
}

.recommendation.low {
  border-left-color: #3b82f6;
  background: #eff6ff;
}

.priority-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  margin-right: 10px;
}

.recommendation.high .priority-badge {
  background: #ef4444;
  color: white;
}

.recommendation.medium .priority-badge {
  background: #f59e0b;
  color: white;
}

.action {
  margin-top: 10px;
  padding: 10px;
  background: rgba(0,0,0,0.05);
  border-radius: 4px;
  font-size: 14px;
}

.loading {
  text-align: center;
  padding: 40px;
  font-size: 18px;
  color: #6b7280;
}

.error {
  background: #fef2f2;
  color: #ef4444;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #fecaca;
}
`;

// Export for documentation
console.log('Frontend integration examples ready!');

