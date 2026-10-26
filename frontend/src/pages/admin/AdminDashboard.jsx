import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { getAdminStats } from '../../api/adminApi';
import './admin.css';

const AdminDashboardPage = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const fetchStats = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getAdminStats();
        if (isMounted) setStats(data);
      } catch (err) {
        console.error('Lỗi khi tải thống kê:', err);
        if (isMounted) setError('Không thể tải dữ liệu thống kê hệ thống.');
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchStats();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="admin-page">
      {/* 1. Hero Banner */}
      <div className="admin-hero">
        <div className="admin-hero-content">
          <div className="admin-hero-tag">Hệ Thống Giám Sát</div>
          <div className="admin-hero-title-row">
            <div className="admin-hero-icon-box" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                <line x1="8" y1="21" x2="16" y2="21" />
                <line x1="12" y1="17" x2="12" y2="21" />
              </svg>
            </div>
            <h1>Bảng Điều Khiển Quản Trị Hệ Thống</h1>
          </div>
          <p className="admin-hero-quote">
            Giám sát tài nguyên máy chủ, số lượng tài khoản và hạn mức sử dụng AI Gemini
          </p>
        </div>
      </div>

      {/* 2. Main Content State */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '48px 20px', color: 'var(--text-muted, #817367)', fontWeight: '700' }}>
          ⏳ Đang tải dữ liệu giám sát hệ thống...
        </div>
      ) : error ? (
        <div style={{ padding: '20px', background: '#fee2e2', color: '#991b1b', borderRadius: '16px', fontWeight: '600' }}>
          {error}
        </div>
      ) : stats ? (
        <>
          {/* Key Metric Cards */}
          <div className="admin-metrics-grid">
            <div className="admin-metric-card gold-border">
              <span className="admin-metric-title">Tổng người dùng</span>
              <span className="admin-metric-val text-gold">{stats.total_users}</span>
              <span className="admin-metric-hint">Tài khoản trong hệ thống</span>
            </div>

            <div className="admin-metric-card green-border">
              <span className="admin-metric-title">Đang hoạt động</span>
              <span className="admin-metric-val text-green">{stats.active_users}</span>
              <span className="admin-metric-hint">Khả dụng đăng nhập</span>
            </div>

            <div className="admin-metric-card red-border">
              <span className="admin-metric-title">Tài khoản bị khóa</span>
              <span className="admin-metric-val text-red">{stats.locked_users}</span>
              <span className="admin-metric-hint">Cần hỗ trợ mở khóa</span>
            </div>

            <div className="admin-metric-card neutral-border">
              <span className="admin-metric-title">Tổng giao dịch</span>
              <span className="admin-metric-val">{stats.total_transactions}</span>
              <span className="admin-metric-hint">Giao dịch toàn hệ thống</span>
            </div>
          </div>

          {/* AI Resource Telemetry */}
          <div className="admin-card-section">
            <div className="admin-card-header">
              <div className="admin-card-header-title">
                <h2>🤖 Giám Sát Tài Nguyên AI Gemini</h2>
                <p>Thống kê các tác vụ AI theo nguyên tắc ẩn danh hóa dữ liệu (Zero-Knowledge Privacy)</p>
              </div>
              <span className="admin-badge-count">
                Tổng: {stats.total_ai_reports} lượt gọi API
              </span>
            </div>

            <div className="admin-ai-grid">
              <div className="admin-ai-item">
                <div>
                  <h4>📈 Báo cáo chi tiêu tháng</h4>
                  <p>Phân tích xu hướng tài chính định kỳ</p>
                </div>
                <span className="admin-ai-item-num">{stats.ai_reports_by_type?.monthly_summary || 0}</span>
              </div>

              <div className="admin-ai-item">
                <div>
                  <h4>💡 Gợi ý ngân sách (50/30/20)</h4>
                  <p>Đề xuất hạn mức danh mục thông minh</p>
                </div>
                <span className="admin-ai-item-num">{stats.ai_reports_by_type?.budget_suggestion || 0}</span>
              </div>

              <div className="admin-ai-item">
                <div>
                  <h4>💬 Trợ lý ảo FinAI Chat</h4>
                  <p>Hỏi đáp tài chính cá nhân tương tác</p>
                </div>
                <span className="admin-ai-item-num">{stats.ai_reports_by_type?.chat_answer || 0}</span>
              </div>
            </div>
          </div>

          {/* Support CTA Banner */}
          <div className="admin-support-banner">
            <div>
              <h3>Cần hỗ trợ người dùng gặp sự cố tài khoản?</h3>
              <p>Mở khóa tài khoản hoặc cấp lại mật khẩu tạm thời ngay tại danh sách người dùng.</p>
            </div>
            <NavLink to="/admin/users" className="btn-admin-cta">
              👥 Đi tới Quản lý người dùng
            </NavLink>
          </div>
        </>
      ) : null}
    </div>
  );
};

export default AdminDashboardPage;
