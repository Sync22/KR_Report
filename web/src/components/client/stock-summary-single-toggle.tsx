"use client";

type Props = {
  date: string;
  selectedStockCode: string | null;
  visibleLimit: number;
  includeSingle: boolean;
  disabled: boolean;
};

export default function StockSummarySingleToggle({ date, selectedStockCode, visibleLimit, includeSingle, disabled }: Props) {
  return (
    <form action={`/daily/${date}/stocks`} method="get" className="stock-single-toggle">
      {selectedStockCode ? <input type="hidden" name="stock" value={selectedStockCode} /> : null}
      <input type="hidden" name="limit" value={visibleLimit} />
      <label><input
        type="checkbox"
        name="include_single"
        value="1"
        defaultChecked={includeSingle}
        disabled={disabled}
        onChange={(event) => event.currentTarget.form?.requestSubmit()}
      />1건 포함</label>
    </form>
  );
}
