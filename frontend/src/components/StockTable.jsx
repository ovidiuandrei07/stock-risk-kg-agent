import RiskBadge from "./RiskBadge";

export default function StockTable({ stocks, onSelect }) {
  return (
    <div className="table-wrap">
      <table className="stock-table">
        <thead>
          <tr>
            <th>Ticker</th>
            <th>Name</th>
            <th>Sector</th>
            <th>Exchange</th>
            <th>Risk level</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((s) => (
            <tr key={s.ticker} onClick={() => onSelect(s.ticker)} tabIndex={0}>
              <td className="stock-table__ticker">{s.ticker}</td>
              <td>{s.name}</td>
              <td>{s.sector}</td>
              <td>{s.exchange}</td>
              <td>
                <RiskBadge level={s.risk_level} value={s.risk_score} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
