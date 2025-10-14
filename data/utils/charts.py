# utils/charts.py
import matplotlib.pyplot as plt
import os

def generate_pie_chart(data: dict, title: str) -> str:
    # data: {'Категория1': сумма1, 'Категория2': сумма2}
    if not data:
        return None
    
    labels = list(data.keys())
    sizes = list(data.values())
    
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    ax.set_title(title)
    
    path = f"data/{title.replace(' ', '_')}.png"
    os.makedirs('data', exist_ok=True)
    plt.savefig(path)
    plt.close()
    return path