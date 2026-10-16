import ChartExplorerClient from "@/components/client/chart-explorer";
import { isChartExplorerTimeframe, type ChartExplorerTimeframe } from "@/domain/chart-explorer";

export default function ChartExplorerPanel({ businessDate, initialSymbol, initialTimeframe }: Readonly<{ businessDate: string; initialSymbol: string; initialTimeframe: ChartExplorerTimeframe }>) {
  return <main className="chart-explorer-page" aria-labelledby="chart-explorer-heading">
    <header className="chart-explorer-intro">
      <div>
        <p className="eyebrow">CHART LAB / LOCAL TEST</p>
        <h1 id="chart-explorer-heading">차트 분석</h1>
        <p>가격·지표·전략 조건·패턴을 기준 시점과 함께 확인합니다. 로컬 감시는 직접 시작해야 작동하며 주문 기능은 없습니다.</p>
      </div>
      <time dateTime={businessDate}>기준일 {businessDate}</time>
    </header>
    <ChartExplorerClient businessDate={businessDate} initialSymbol={initialSymbol} initialTimeframe={initialTimeframe} />
  </main>;
}
