export function addNonPassiveChartWheelListener(target: EventTarget, onWheel: (event: WheelEvent) => void): () => void {
  const listener: EventListener = (rawEvent) => {
    const event = rawEvent as WheelEvent;
    if (!event.deltaY) return;
    event.preventDefault();
    onWheel(event);
  };
  target.addEventListener("wheel", listener, { passive: false });
  return () => target.removeEventListener("wheel", listener);
}
