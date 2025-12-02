import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import RadioButtons, TextBox, Button

#stale
ROWS = 200
COLS = 200

# zmienne globalne
grid = None
BOUNDARY = "periodyczny"   # "periodyczny" lub "odbijający"
NEIGHBORHOOD = "moore"     # "moore" albo "neumann"
SURVIVE = {2, 3}
BIRTH = {3}
STEPS = 100
INIT_NAME = "Glider"
anim = None

#parsowanie reguly
def parse_rule(rule_str):
    """Parsuje regułę typu 'S23/B3' → zbiory SURVIVE, BIRTH."""
    rule_str = rule_str.strip().upper()
    try:
        s_part, b_part = rule_str.split("/")
    except ValueError:
        return {2, 3}, {3}
    #rozdzielamy na S i B
    if not (s_part.startswith("S") and b_part.startswith("B")):
        return {2, 3}, {3}

    survive = {int(ch) for ch in s_part[1:] if ch.isdigit()}
    birth = {int(ch) for ch in b_part[1:] if ch.isdigit()}
    if not survive:
        survive = {2, 3}
    if not birth:
        birth = {3}
    return survive, birth

#tab wypel 0
def empty_grid():
    return np.zeros((ROWS, COLS), dtype=int)


def place_center(grid, pattern):
    """Wstawia mały wzór pattern mniej więcej na środek planszy."""
    pr = [p[0] for p in pattern]
    pc = [p[1] for p in pattern]
    min_r, min_c = min(pr), min(pc)
    max_r, max_c = max(pr), max(pc)
    norm = [(r - min_r, c - min_c) for r, c in pattern]

    off_r = ROWS // 2 - max_r // 2
    off_c = COLS // 2 - max_c // 2
    #normalizacja wzoru w kierunku srodka planszy
    for r, c in norm:
        rr = ROWS // 2 - max_r // 2 + r
        cc = COLS // 2 - max_c // 2 + c
        if 0 <= rr < ROWS and 0 <= cc < COLS:
            grid[rr, cc] = 1    #komorki na 1 - zywe


def pattern_glider():
    return [(0, 2), (1, 0), (1, 2), (2, 1), (2, 2)]


def pattern_still():
    return [(0, 0), (0, 1), (1, 0), (1, 1)]


def pattern_pentadecathlon():
    # Oscylator z min. 15 komorek
    return [
        (1, 0), (1, 1), (1, 2),
        (1, 4), (1, 5), (1, 6),
        (1, 8), (1, 9), (1,10),
        (0, 3), (2, 3),
        (0, 7), (2, 7),
        (1, 3), (1, 7),
    ]


def init_grid(name, density=0.2):
    """Tworzy siatkę dla danego stanu początkowego."""
    g = empty_grid()
    n = name.lower()
    if n == "glider":
        place_center(g, pattern_glider())
    elif n in ("niezmienny", "still", "blok"):
        place_center(g, pattern_still())
    elif n in ("losowy", "random", "dowolny"):
        g[:] = (np.random.rand(ROWS, COLS) < density).astype(int)
    elif n in ("pentadecathlon", "oscylator"):
        place_center(g, pattern_pentadecathlon())
    else:
        g[:] = (np.random.rand(ROWS, COLS) < density).astype(int)
    return g

#indeks zawinie sie na druga str
def periodic(i, n):
    return i % n

#jezeli za plansza - odbjamy jak w lustrze
def reflect(i, n):
    if i < 0:
        return -i
    if i >= n:
        return 2 * n - i - 2
    return i

#sasiedztwo
def count_neighbors(grid, r, c, boundary):
    """Liczy sąsiadów według wybranego sąsiedztwa (Moore / von Neumann)."""
    alive = 0

    if NEIGHBORHOOD == "moore":
        deltas = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),            (0, 1),
            (1, -1),  (1, 0),   (1, 1),
        ]
    else:  # "neumann"
        deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
#dla kazdego sasiada przesuwamy sie o (dr,dc)
    for dr, dc in deltas:
        rr = r + dr
        cc = c + dc
        #poprawiamy wsp wg typu brzegu
        if boundary == "periodyczny":
            rr = periodic(rr, ROWS)
            cc = periodic(cc, COLS)
        else:  # odbijający
            rr = reflect(rr, ROWS)
            cc = reflect(cc, COLS)
        alive += grid[rr, cc] #zliczamy zywe
    return alive

#jednek krok automatu -> IMPLEMENTACJA REg s../b..
def step_grid(grid, boundary, survive, birth):
    new = empty_grid()
    for r in range(ROWS):
        #dla kazdej zywej kom lizczymy l sasiadow n 
        for c in range(COLS):
            n = count_neighbors(grid, r, c, boundary)
            if grid[r, c] == 1: #jesli zywa - czy w S
                new[r, c] = 1 if n in survive else 0
            else:# jesli martwa sprawdzamy czy n w B
                new[r, c] = 1 if n in birth else 0
    return new


#gui
fig = plt.figure(figsize=(11, 6))
gs = fig.add_gridspec(1, 2, width_ratios=[3, 1])

ax_grid = fig.add_subplot(gs[0, 0])
ax_panel = fig.add_subplot(gs[0, 1])
ax_panel.axis("off")

# poczatkowa siatka (default)
grid = init_grid("glider")
im = ax_grid.imshow(grid, cmap="binary", interpolation="nearest", vmin=0, vmax=1)
ax_grid.set_xticks([])
ax_grid.set_yticks([])
title = ax_grid.set_title("Gra w życie 2D – jeszcze nie wystartowano")

# --- panel: radio przyciski i pola tekstowe ---

# Naglowki sekcji
ax_title_init = fig.add_axes([0.72, 0.84, 0.25, 0.04])
ax_title_init.axis("off")
ax_title_init.text(0, 0.5, "Stan początkowy", fontsize=11, fontweight="bold")

ax_title_bound = fig.add_axes([0.72, 0.66, 0.25, 0.04])
ax_title_bound.axis("off")
ax_title_bound.text(0, 0.5, "Brzeg", fontsize=11, fontweight="bold")

ax_title_neigh = fig.add_axes([0.72, 0.48, 0.25, 0.04])
ax_title_neigh.axis("off")
ax_title_neigh.text(0, 0.5, "Sąsiedztwo", fontsize=11, fontweight="bold")

ax_title_rule = fig.add_axes([0.72, 0.32, 0.25, 0.04])
ax_title_rule.axis("off")
ax_title_rule.text(0, 0.5, "Reguła S/B", fontsize=11, fontweight="bold")

ax_title_steps = fig.add_axes([0.72, 0.22, 0.25, 0.04])
ax_title_steps.axis("off")
ax_title_steps.text(0, 0.5, "Kroki", fontsize=11, fontweight="bold")

# Widgety

ax_init = fig.add_axes([0.72, 0.72, 0.25, 0.11])
radio_init = RadioButtons(
    ax_init,
    labels=["Glider", "Niezmienny", "Losowy", "Pentadecathlon"],
    active=0
)

ax_bound = fig.add_axes([0.72, 0.58, 0.25, 0.08])
radio_bound = RadioButtons(
    ax_bound,
    labels=["Periodyczny", "Odbijający"],
    active=0
)

ax_neigh = fig.add_axes([0.72, 0.40, 0.25, 0.08])
radio_neigh = RadioButtons(
    ax_neigh,
    labels=["Moore (8)", "von Neumann (4)"],
    active=0
)

ax_rule = fig.add_axes([0.72, 0.28, 0.25, 0.04])
text_rule = TextBox(ax_rule, "", initial="S23/B3")

ax_steps = fig.add_axes([0.72, 0.18, 0.25, 0.04])
text_steps = TextBox(ax_steps, "", initial="100")

ax_button = fig.add_axes([0.72, 0.08, 0.25, 0.06])
button_start = Button(ax_button, "START", color="lightgreen", hovercolor="green")


def on_start(event):
    """Callback przycisku START – odczytuje ustawienia i uruchamia animację."""
    global grid, BOUNDARY, SURVIVE, BIRTH, STEPS, INIT_NAME, NEIGHBORHOOD, anim

    # --- stan poczatkowy ---
    init_label = radio_init.value_selected  # np. "Glider"
    INIT_NAME = init_label
    if init_label == "Glider":
        init_internal = "glider"
    elif init_label == "Niezmienny":
        init_internal = "niezmienny"
    elif init_label == "Losowy":
        init_internal = "losowy"
    else:
        init_internal = "pentadecathlon"

    # --- warunek brzegowy ---
    bound_label = radio_bound.value_selected
    if bound_label.startswith("Perio"):
        BOUNDARY = "periodyczny"
    else:
        BOUNDARY = "odbijający"

    # --- sasiedztwo ---
    neigh_label = radio_neigh.value_selected
    if neigh_label.startswith("Moore"):
        NEIGHBORHOOD = "moore"
    else:
        NEIGHBORHOOD = "neumann"

    # --- regula S/B ---
    rule_str = text_rule.text.strip()
    if rule_str == "":
        rule_str = "S23/B3"
    SURVIVE, BIRTH = parse_rule(rule_str)
    rule_display = rule_str.upper()

    # --- liczba krokow ---
    try:
        steps_val = int(text_steps.text)
        if steps_val < 30:
            steps_val = 30
    except ValueError:
        steps_val = 100
    STEPS = steps_val
    text_steps.set_val(str(STEPS))

    # --- nowa siatka startowa ---
    grid = init_grid(init_internal)
    alive0 = int(grid.sum())

    ax_grid.set_title(
        f"Gra w życie 2D | start: {INIT_NAME}, brzeg: {BOUNDARY}, "
        f"sąsiedztwo: {NEIGHBORHOOD}, reguła: {rule_display}\n"
        f"Krok 0/{STEPS} | żywych komórek: {alive0}"
    )
    im.set_data(grid)

    # --- animacja ---
    def update(frame):
        global grid
        grid = step_grid(grid, BOUNDARY, SURVIVE, BIRTH)
        im.set_data(grid)
        alive = int(grid.sum())
        ax_grid.set_title(
            f"Gra w życie 2D | start: {INIT_NAME}, brzeg: {BOUNDARY}, "
            f"sąsiedztwo: {NEIGHBORHOOD}, reguła: {rule_display}\n"
            f"Krok {frame+1}/{STEPS} | żywych komórek: {alive}"
        )
        return im,

    anim = FuncAnimation(
        fig,
        update,
        frames=STEPS,
        interval=100,
        repeat=False
    )
    fig.canvas.draw_idle()


button_start.on_clicked(on_start)

plt.show()
