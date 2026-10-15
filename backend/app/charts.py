"""Визуализация статистики через matplotlib (PNG в стиле метал-постера)."""
import io

import matplotlib

matplotlib.use("Agg")  # без графического окна, рисуем в память
import matplotlib.pyplot as plt  # noqa: E402

RED, GOLD, STEEL, BG = "#d4141c", "#f5b700", "#c9ccd1", "#0b0b0d"


def stats_chart(stats: dict) -> bytes:
    cats = stats["categories"]
    names = [c["name"] for c in cats.values()]
    stock = [c["stock_units"] for c in cats.values()]
    revenue = [c["revenue"] for c in cats.values()]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), facecolor=BG)
    for ax, values, color, title in (
        (ax1, stock, STEEL, "Остаток на складе, шт."),
        (ax2, revenue, RED, "Выручка по категориям, $"),
    ):
        ax.set_facecolor(BG)
        bars = ax.barh(names, values, color=color, edgecolor=GOLD, linewidth=1.2)
        ax.bar_label(bars, fmt="%.0f", color="white", padding=4, fontsize=9)
        ax.set_title(title, color=GOLD, fontsize=13, fontweight="bold")
        ax.tick_params(colors="white")
        ax.invert_yaxis()
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#555")

    fig.suptitle(f"Заказов: {stats['orders_count']}   •   Выручка: ${stats['revenue_total']:,.0f}",
                 color="white", fontsize=12)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, facecolor=BG)
    plt.close(fig)
    return buf.getvalue()
