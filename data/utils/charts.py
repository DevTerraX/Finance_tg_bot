import matplotlib.pyplot as plt

from typing import Optional

from .storage import get_user_file_path


def generate_pie_chart(data: dict, title: str, user_id: int) -> Optional[str]:
    """
    Генерирует круговую диаграмму и сохраняет в папке пользователя.
    """
    if not data:
        return None

    labels = list(data.keys())
    sizes = list(data.values())

    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    ax.set_title(title)

    filename = f"{title.replace(' ', '_')}.png"
    path = get_user_file_path(user_id, "charts", filename)
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    return str(path)
