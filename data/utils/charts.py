from typing import Optional

import matplotlib.pyplot as plt
from matplotlib import cm

from .storage import get_user_file_path


def generate_pie_chart(data: dict, title: str, user_id: int) -> Optional[str]:
    """
    Генерирует круговую диаграмму с улучшенным оформлением и сохраняет её в папке пользователя.
    """
    if not data:
        return None

    labels = list(data.keys())
    sizes = list(data.values())

    plt.style.use('seaborn-v0_8-pastel')
    display_title = title.replace('_', ' ').strip()

    fig, ax = plt.subplots(figsize=(6, 6), facecolor='white')
    colors = cm.get_cmap('Set2')(range(len(sizes)))

    total = sum(sizes)

    def _autopct(pct: float) -> str:
        value = pct * total / 100
        return f"{pct:.1f}%\n{value:,.0f}".replace(',', ' ')

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct=_autopct,
        startangle=120,
        colors=colors,
        pctdistance=0.78,
        wedgeprops=dict(linewidth=1.2, edgecolor='white')
    )
    ax.axis('equal')
    ax.set_title(display_title, fontsize=16, fontweight='bold', color='#2b2d42', pad=20)

    for text in texts:
        text.set_fontsize(11)
        text.set_color('#2b2d42')
    for autotext in autotexts:
        autotext.set_fontsize(10)
        autotext.set_color('#2b2d42')

    ax.legend(
        wedges,
        labels,
        title="Категории",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.35, 1),
        frameon=False,
        fontsize=10,
        title_fontsize=11
    )

    fig.tight_layout()

    filename = f"{display_title.replace(' ', '_')}.png"
    path = get_user_file_path(user_id, "charts", filename)
    plt.savefig(path, bbox_inches='tight')
    plt.close(fig)
    return str(path)
