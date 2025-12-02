from typing import List, Tuple, Dict
#stala lista trojek - 8 bitowa l.
NEIGH_PATTERNS = [
    (1,1,1), 
    (1,1,0),
    (1,0,1),
    (1,0,0),
    (0,1,1),
    (0,1,0),
    (0,0,1),
    (0,0,0),
]


#numer na ciag bit -> przypisanoie bitow do konkret trojek
def wolfram_to_table(rule_number: int) -> Dict[Tuple[int,int,int], int]:
    """Konwersja numeru Wolframa (0–255) na tabelę reguły."""
    bits = f"{rule_number:08b}" #nr na bity
    return {pat: int(bits[i]) for i, pat in enumerate(NEIGH_PATTERNS)}

#tabela reguly - dla wyn mojej reguly
def table_to_wolfram(table: Dict[Tuple[int,int,int], int]) -> int:
    bits = "".join(str(table[pat]) for pat in NEIGH_PATTERNS)
    return int(bits, 2)

def my_rule(left: int, center: int, right: int) -> int:
    """Autorska regula:
    - jesli obaj sasiedzi = 1 → odwroc srodkowa komorke
    - jesli sasiedzi rozni → ustaw 1
    - inaczej → 0
    """
    if left == 1 and right == 1:
        return 1 - center
    if left != right:
        return 1
    return 0

def my_rule_table() -> Dict[Tuple[int,int,int], int]:
    return {pat: my_rule(*pat) for pat in NEIGH_PATTERNS}


# ewolucja automatu - 1 krok
def next_state_periodic(state: List[int], table: Dict[Tuple[int,int,int], int]) -> List[int]:
    """Zwraca następny stan (periodyczny warunek brzegowy)."""
    n = len(state)
    new_state = [0]*n
    for i in range(n):
        left = state[(i-1) % n]
        center = state[i]
        right = state[(i+1) % n]
        new_state[i] = table[(left, center, right)]
    return new_state

def render(state: List[int]) -> str:
    """Zamienia stan [0,1,0,...] na ciąg znaków ASCII."""
    return "".join("█" if x == 1 else " " for x in state)


def main():
    print(" Automat komórkowy 1D ")
    print("Warunek brzegowy: periodyczny\n")

    # pobieranie danych od uzytkownika
    try:
        n = int(input("Podaj rozmiar automatu (N>0): "))
        if n <= 0:
            raise ValueError("Rozmiar musi być > 0")
    except ValueError as e:
        print(f"Błąd: {e}")
        return

    try:
        steps = int(input("Podaj liczbę iteracji (>=1): "))
        if steps < 1:
            raise ValueError("Liczba iteracji musi być >= 1")
    except ValueError as e:
        print(f"Błąd: {e}")
        return

    # wybor reguly
    rule_input = input("Podaj regułę (0–255 lub 'my' dla własnej): ").strip().lower()
    if rule_input == "my":
        table = my_rule_table()
        rule_num = table_to_wolfram(table)
        print(f"Wybrano regułę autorską (numer Wolframa: {rule_num})")
    else:
        try:
            r = int(rule_input)
            if r < 0 or r > 255:
                raise ValueError("Numer reguły spoza zakresu 0–255")
            table = wolfram_to_table(r)
            rule_num = r
        except ValueError:
            print("Błąd: niepoprawna reguła.")
            return

    # stan poczatkowy (srodkowa komorka aktywna)
    state = [0]*n
    state[n//2] = 1

    # Wyswietlanie ewolucji
    print(f"\nReguła: {rule_num}")
    for _ in range(steps):
        print(render(state))
        state = next_state_periodic(state, table)

    print("\nGotowe!")

if __name__ == "__main__":
    main()
