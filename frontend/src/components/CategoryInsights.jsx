import { memo, useMemo, useState, useRef } from 'react';
import { centsToDecimal, decimalToCents, formatVndDecimal, percentageOf } from '../utils/money';

const CategoryInsights = ({ categories }) => {
  const [viewType, setViewType] = useState('overview'); // 'overview', 'expense', or 'income'
  const toggleRef = useRef(null);

  const customSmoothScroll = (element, duration = 350) => {
    const targetPosition = element.getBoundingClientRect().top + window.scrollY - 32;
    const startPosition = window.scrollY;
    const distance = targetPosition - startPosition;
    let startTime = null;

    const easeOutQuart = (t) => 1 - Math.pow(1 - t, 4);

    const animation = (currentTime) => {
      if (startTime === null) startTime = currentTime;
      const timeElapsed = currentTime - startTime;
      const progress = Math.min(timeElapsed / duration, 1);
      
      window.scrollTo(0, startPosition + distance * easeOutQuart(progress));
      
      if (timeElapsed < duration) {
        requestAnimationFrame(animation);
      }
    };
    requestAnimationFrame(animation);
  };

  const handleTabSwitch = (type) => {
    setViewType(type);
    setTimeout(() => {
      if (toggleRef.current) {
        customSmoothScroll(toggleRef.current, 350);
      }
    }, 50);
  };

  const insights = useMemo(() => {
    const rows = categories.map((category) => ({
      ...category,
      expenseCents: decimalToCents(category.expense_amount),
      incomeCents: decimalToCents(category.income_amount),
    }));
    const expenseTotal = rows.reduce((total, row) => total + row.expenseCents, 0n);
    const incomeTotal = rows.reduce((total, row) => total + row.incomeCents, 0n);
    const transactionCount = rows.reduce(
      (total, row) => total + Number(row.transaction_count || 0),
      0,
    );

    // Expense logic
    const expenseRanked = rows
      .filter((row) => row.expenseCents > 0n)
      .sort((first, second) => (
        first.expenseCents === second.expenseCents
          ? first.name.localeCompare(second.name, 'vi')
          : first.expenseCents > second.expenseCents ? -1 : 1
      ));

    let expCursor = 0;
    const expSegments = expenseRanked.map((row) => {
      const width = percentageOf(row.expenseCents, expenseTotal);
      const segment = `${row.color} ${expCursor}% ${Math.min(100, expCursor + width)}%`;
      expCursor += width;
      return segment;
    });
    if (expCursor < 100) expSegments.push(`#EAE4D8 ${expCursor}% 100%`);

    // Income logic
    const incomeRanked = rows
      .filter((row) => row.incomeCents > 0n)
      .sort((first, second) => (
        first.incomeCents === second.incomeCents
          ? first.name.localeCompare(second.name, 'vi')
          : first.incomeCents > second.incomeCents ? -1 : 1
      ));

    let incCursor = 0;
    const incSegments = incomeRanked.map((row) => {
      const width = percentageOf(row.incomeCents, incomeTotal);
      const segment = `${row.color} ${incCursor}% ${Math.min(100, incCursor + width)}%`;
      incCursor += width;
      return segment;
    });
    if (incCursor < 100) incSegments.push(`#EAE4D8 ${incCursor}% 100%`);

    return {
      expenseTotal,
      incomeTotal,
      transactionCount,
      expenseRanked,
      incomeRanked,
      expenseGradient: expSegments.length ? `conic-gradient(${expSegments.join(', ')})` : '#EAE4D8',
      incomeGradient: incSegments.length ? `conic-gradient(${incSegments.join(', ')})` : '#EAE4D8',
    };
  }, [categories]);

  const activeRanked = viewType === 'expense' ? insights.expenseRanked : insights.incomeRanked;
  const activeTotal = viewType === 'expense' ? insights.expenseTotal : insights.incomeTotal;
  const activeGradient = viewType === 'expense' ? insights.expenseGradient : insights.incomeGradient;
  const activePropCents = viewType === 'expense' ? 'expenseCents' : 'incomeCents';
  const activePropAmount = viewType === 'expense' ? 'expense_amount' : 'income_amount';

  return (
    <section className="category-insights fade-in" aria-labelledby="category-insights-title">
      <div className="insight-view-toggle" ref={toggleRef}>
        <button 
          className={`toggle-btn ${viewType === 'overview' ? 'active' : ''}`}
          onClick={() => handleTabSwitch('overview')}
        >
          <span className="toggle-icon">⚖️</span> Tổng quan
        </button>
        <button 
          className={`toggle-btn ${viewType === 'expense' ? 'active' : ''}`}
          onClick={() => handleTabSwitch('expense')}
        >
          <span className="toggle-icon">📉</span> Thống kê Chi tiêu
        </button>
        <button 
          className={`toggle-btn ${viewType === 'income' ? 'active' : ''}`}
          onClick={() => handleTabSwitch('income')}
        >
          <span className="toggle-icon">📈</span> Thống kê Thu nhập
        </button>
      </div>

      {viewType === 'overview' && (
        <div className="insight-charts">
          <article className="insight-overview-panel">
            <div className="panel-header" style={{ marginBottom: '20px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: '700' }}>Cán cân Tài chính</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Tổng quan thu chi trong kỳ.</p>
            </div>
            <div className="overview-panel-content">
              <div className="overview-balance">
                <div className="balance-item">
                  <span>Tổng Thu nhập</span>
                  <strong className="text-success">+{formatVndDecimal(centsToDecimal(insights.incomeTotal))}</strong>
                </div>
                <div className="balance-item">
                  <span>Tổng Chi tiêu</span>
                  <strong className="text-error">-{formatVndDecimal(centsToDecimal(insights.expenseTotal))}</strong>
                </div>
                <div className="balance-item">
                  <span>Số Giao dịch</span>
                  <strong style={{ color: '#1e293b' }}>{insights.transactionCount}</strong>
                </div>
                <div className="balance-item balance-total">
                  <span>Số dư (Thu - Chi)</span>
                  <strong className={insights.incomeTotal - insights.expenseTotal >= 0n ? 'text-success' : 'text-error'}>
                    {formatVndDecimal(centsToDecimal(insights.incomeTotal - insights.expenseTotal))}
                  </strong>
                </div>
              </div>
            </div>
          </article>
          
          <article className="insight-overview-panel">
            <div className="panel-header" style={{ marginBottom: '20px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: '700' }}>Biến động lớn nhất</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Top danh mục thu/chi nhiều nhất.</p>
            </div>
            <div className="overview-panel-content" style={{ gap: '20px' }}>
              {insights.incomeRanked.length > 0 && (
                <div className="overview-top-cats">
                  <h4>Thu nhiều nhất</h4>
                  <div className="top-cat-item">
                    <span><i style={{ '--cat-color': insights.incomeRanked[0].color }} /> {insights.incomeRanked[0].name}</span>
                    <strong className="text-success">+{formatVndDecimal(insights.incomeRanked[0].income_amount)}</strong>
                  </div>
                </div>
              )}
              {insights.expenseRanked.length > 0 && (
                <div className="overview-top-cats">
                  <h4>Chi nhiều nhất</h4>
                  <div className="top-cat-item">
                    <span><i style={{ '--cat-color': insights.expenseRanked[0].color }} /> {insights.expenseRanked[0].name}</span>
                    <strong className="text-error">-{formatVndDecimal(insights.expenseRanked[0].expense_amount)}</strong>
                  </div>
                </div>
              )}
              {insights.incomeRanked.length === 0 && insights.expenseRanked.length === 0 && (
                <p className="chart-empty">Chưa có giao dịch nào trong kỳ này.</p>
              )}
            </div>
          </article>
        </div>
      )}

      {viewType !== 'overview' && (
        <div className="insight-charts">
          <article className="insight-donut-panel">
            <div className="panel-header" style={{ marginBottom: '20px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: '700' }}>Cơ cấu {viewType === 'expense' ? 'chi tiêu' : 'thu nhập'}</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Tỷ trọng theo toàn bộ danh mục trong kỳ.</p>
            </div>
            <div className="insight-donut-content">
              <div
                className="insight-donut"
                style={{ '--donut-gradient': activeGradient }}
                role="img"
                aria-label={`Tổng ${viewType === 'expense' ? 'chi' : 'thu'} ${formatVndDecimal(centsToDecimal(activeTotal))}`}
              >
                <span><small>Tổng {viewType === 'expense' ? 'chi' : 'thu'}</small>{formatVndDecimal(centsToDecimal(activeTotal))}</span>
              </div>
              <div className="insight-legend">
                {activeRanked.slice(0, 5).map((row) => (
                  <div key={row.id}>
                    <i style={{ '--legend-color': row.color }} />
                    <span>{row.name}</span>
                    <strong>{percentageOf(row[activePropCents], activeTotal).toFixed(1)}%</strong>
                  </div>
                ))}
                {activeRanked.length === 0 && <p>Chưa có khoản {viewType === 'expense' ? 'chi' : 'thu'} trong kỳ này.</p>}
              </div>
            </div>
          </article>

          <article className="insight-ranking-panel">
            <div className="panel-header" style={{ marginBottom: '20px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: '700' }}>Danh mục {viewType === 'expense' ? 'chi' : 'thu'} nhiều nhất</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Top 6 theo số tiền đã {viewType === 'expense' ? 'chi' : 'thu'}.</p>
            </div>
            <div className="insight-ranking">
              {activeRanked.slice(0, 6).map((row) => (
                <div className="ranking-row" key={row.id}>
                  <div><span>{row.name}</span><strong>{formatVndDecimal(row[activePropAmount])}</strong></div>
                  <span className="ranking-track">
                    <i style={{
                      '--bar-color': row.color,
                      '--bar-width': `${percentageOf(row[activePropCents], activeRanked[0][activePropCents])}%`,
                    }} />
                  </span>
                </div>
              ))}
              {activeRanked.length === 0 && <p className="chart-empty">Biểu đồ sẽ xuất hiện khi có giao dịch {viewType === 'expense' ? 'chi' : 'thu'}.</p>}
            </div>
          </article>
        </div>
      )}
    </section>
  );
};

export default memo(CategoryInsights);
