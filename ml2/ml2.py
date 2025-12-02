import numpy as np
from PIL import Image
import os

#skalowanie zbyt duzego obrazu
def resize_nearest(img_array, max_size=512):
    h, w = img_array.shape
    longer = max(w, h)

    # gdy obraz już jest maly-> nic nie rób
    if longer <= max_size:
        return img_array
    #wsp skalownia
    scale = max_size / float(longer)
    new_w = int(w * scale)
    new_h = int(h * scale)
    #mniejsza macierz
    out = np.zeros((new_h, new_w), dtype=np.float32)

    for y2 in range(new_h):
        for x2 in range(new_w):
            # dla kazdego nowego pix w out wybieram pix z org
            src_x = int(x2 / scale)
            src_y = int(y2 / scale)
            # zabezp na granicy
            if src_x >= w:
                src_x = w - 1
            if src_y >= h:
                src_y = h - 1
            out[y2, x2] = img_array[src_y, src_x]

    return out

def load_image_gray(path, max_size=512):
   # wczytuje obraz z pliku jako 1 kanał (grayscale) - zmiana na tab liczb
  
    img = Image.open(path).convert("L") #zmiana na skale szarosci
    arr = np.array(img, dtype=np.float32)
    arr = resize_nearest(arr, max_size=max_size)
    return arr

def save_image(array, path):
   # zapisuje macierz (0..255) 
    arr = np.clip(array, 0, 255).astype(np.uint8)
    Image.fromarray(arr).save(path)#zapis do png 

# Warunki brzegowe 
# 1 padding
def pad_replicate(img, r):
    #tworze ramke wokol obrazu
    h, w = img.shape
    padded = np.zeros((h + 2*r, w + 2*r), dtype=img.dtype)
    #piks ramki kopiuja najblizszy pix z brzegu obrazu
    # r-promien 

    # srodek
    padded[r:r+h, r:r+w] = img

    # gora/dol
    padded[:r, r:r+w] = img[0:1, :]
    padded[r+h:, r:r+w] = img[h-1:h, :]

    # lewo/prawo
    padded[:, :r] = padded[:, r:r+1]
    padded[:, r+w:] = padded[:, r+w-1:r+w]

    return padded

#2 odbicie lustrzane przy brzegach 
def pad_reflect(img, r):

   # odbija gore, dol, lewo, prawo i narozniki bez bledow wym
    h, w = img.shape
    padded = np.zeros((h + 2*r, w + 2*r), dtype=img.dtype)

    # wstawiamy oryginal w srodek
    padded[r:r+h, r:r+w] = img

    # odbicie gora/dol
    padded[:r, r:r+w] = img[r:0:-1, :]           
    padded[r+h:, r:r+w] = img[h-2:h-r-2:-1, :]   

    # odbicie lewo/prawo
    padded[:, :r] = padded[:, 2*r:r:-1]
    padded[:, r+w:] = padded[:, w+r-2:w-2:-1]

    # narozniki
    padded[:r, :r] = padded[r:2*r, r:2*r][::-1, ::-1]           # lewy gorny
    padded[:r, r+w:] = padded[r:2*r, w:w+r][::-1, ::-1]         # prawy gorny
    padded[r+h:, :r] = padded[h:h+r, r:2*r][::-1, ::-1]         # lewy dolny
    padded[r+h:, r+w:] = padded[h:h+r, w:w+r][::-1, ::-1]       # prawy dolny

    return padded

# Konwolucja (splot)
def convolve(img, kernel, padding_mode="reflect"):
    #wybor - reflect / replicate 

    #wycinamy z obrazu sasiedztwo pix 
    ksize = kernel.shape[0]
    assert ksize == kernel.shape[1], "kernel musi być kwadratem"
    assert ksize % 2 == 1, "kernel musi mieć nieparzysty rozmiar (3,5,7,...)"

    r = ksize // 2

    if padding_mode == "replicate":
        padded = pad_replicate(img, r)
    elif padding_mode == "reflect":
        padded = pad_reflect(img, r)
    else:
        raise ValueError("Nieznane padding_mode: " + str(padding_mode))

    h, w = img.shape
    out = np.zeros_like(img, dtype=np.float32)

    # mnozymy elementowo przez kernel
    for y in range(h):
        for x in range(w):
            region = padded[y:y+ksize, x:x+ksize]  # okno pod kernelem
            out[y, x] = np.sum(region * kernel) #suma
    # zapis do wyjscoa
    return out


# generatory masek filtrow

def gaussian_kernel(radius, sigma=None):
    if sigma is None:
        sigma = radius / 2 + 1e-6
    size = 2 * radius + 1
    #tworze siatke wsp x i y w zakresie od -r do r 
    ax = np.arange(-radius, radius + 1, dtype=np.float32)
    X, Y = np.meshgrid(ax, ax)
    #kazdy pkt liczymy ze wzoru (f.gaussa) :
    kernel = np.exp(-(X**2 + Y**2) / (2 * sigma**2))
    kernel /= np.sum(kernel)
    return kernel

#wygladzenie
def low_pass_box(radius):
    size = 2 * radius + 1
    ax = np.arange(-radius, radius + 1, dtype=np.float32)
    X, Y = np.meshgrid(ax, ax)
    #dajemy najw wage w srodku
    dist = np.sqrt(X**2 + Y**2)
    #im dalej od sr tym mniejsza waga 
    kernel = 1.0 / (1.0 + dist)
    kernel /= np.sum(kernel)
    return kernel

#wyostrzenie 
def high_pass(radius):
    size = 2 * radius + 1
    #ujemne wart dookokla i duza dodatnia w srodku -> suma ~0
    k = -np.ones((size, size), dtype=np.float32)
    k[radius, radius] = (size * size) - 1
    k /= (size * size)
    return k

# Morfologia binarna

#tworzy kwadrat el strukt (same 1)
def get_structuring_element(r):
    #r=1 -> 3x3, r=2 -> 5x5 itd
    return np.ones((2*r+1, 2*r+1), dtype=np.uint8)

#erozja
def erode(binary, r):
   # Piks = 1 tylko gdy wszyscy sasiedz to 1
    #-> biały obszar sie kurczy

    se = get_structuring_element(r)
    pad = pad_replicate(binary, r)  
    h, w = binary.shape
    out = np.zeros_like(binary, dtype=np.uint8)

    for y in range(h):
        for x in range(w):
            region = pad[y:y+2*r+1, x:x+2*r+1]
            out[y, x] = 1 if np.all(region[se == 1] == 1) else 0

    return out

#dylatacja 
def dilate(binary, r):
    #piks= 1 jesli w sas choc jeden sas to 1 
    #-> bialy obszar puchnie/ coraz grubszy

    se = get_structuring_element(r)
    pad = pad_replicate(binary, r)
    h, w = binary.shape
    out = np.zeros_like(binary, dtype=np.uint8)

    for y in range(h):
        for x in range(w):
            region = pad[y:y+2*r+1, x:x+2*r+1]
            out[y, x] = 1 if np.any(region[se == 1] == 1) else 0

    return out

#otwarcie = erozja -> dylatacja
def opening(binary, r):
    #czysci szumy - zostawia glowne obiekt
    return dilate(erode(binary, r), r)

#zamkniecie = dylatacja -> erozja 
def closing(binary, r):
    # najpierw domykamy dziury w obiekcie, potem wygladzamy 
    return erode(dilate(binary, r), r)


def main():
    os.makedirs("results", exist_ok=True)

    # 1. wczytanie 
    img = load_image_gray("kot.png")

    # 2. budowa filtr na podst r
    g_kernel_small = gaussian_kernel(radius=2)           # Gauss mały
    g_kernel_big   = gaussian_kernel(radius=4, sigma=3)  # Gauss wiekszy (modyf)
    l_kernel       = low_pass_box(radius=1)              
    h_kernel       = high_pass(radius=1)                 

    # 3. zast filtrow:  replicate  vs  reflect
    img_gauss_rep   = convolve(img, g_kernel_small, padding_mode="replicate")
    img_gauss_refl  = convolve(img, g_kernel_small, padding_mode="reflect")

    img_low_rep     = convolve(img, l_kernel, padding_mode="replicate")
    img_low_refl    = convolve(img, l_kernel, padding_mode="reflect")

    img_high_rep    = convolve(img, h_kernel, padding_mode="replicate")
    img_high_refl   = convolve(img, h_kernel, padding_mode="reflect")

    img_gauss_big_rep  = convolve(img, g_kernel_big, padding_mode="replicate")
    img_gauss_big_refl = convolve(img, g_kernel_big, padding_mode="reflect")

    # 4. normalizacja high-pass do zapisu: high-pass może mieć wart (-)
    # więc przesuwamy i rozciag do zakresu 0..255
    def to_visible(arr):
        mn, mx = arr.min(), arr.max()
        if mx - mn < 1e-6:
            return np.zeros_like(arr, dtype=np.float32)
        return (arr - mn) / (mx - mn) * 255.0

    img_high_rep_vis  = to_visible(img_high_rep)
    img_high_refl_vis = to_visible(img_high_refl)

    # 5. binaryzacja obrazu -> potrzebna do morfologii
    binary = (img > 110).astype(np.uint8)

    # 6. morfologia na binarnym obrazie
    ero = erode(binary, 1)
    dil = dilate(binary, 1)
    opn = opening(binary, 1)
    cls = closing(binary, 1)

    # 7. Zapis 
    # oryginal
    save_image(img, "results/0_original.png")

    # Gauss (maly)
    save_image(img_gauss_rep,  "results/1_gauss_replicate.png")
    save_image(img_gauss_refl, "results/2_gauss_reflect.png")

    # Gauss (wiekszy) - modyf filtru 
    save_image(img_gauss_big_rep,  "results/3_gauss_big_replicate.png")
    save_image(img_gauss_big_refl, "results/4_gauss_big_reflect.png")

    # low-pass (box blur)
    save_image(img_low_rep,   "results/5_lowpass_replicate.png")
    save_image(img_low_refl,  "results/6_lowpass_reflect.png")

    # high-pass (wyostrzenie/kraw) znormal
    save_image(img_high_rep_vis,   "results/7_highpass_replicate.png")
    save_image(img_high_refl_vis,  "results/8_highpass_reflect.png")

    # obraz binarny + morfologia
    save_image(binary * 255,  "results/9_binary.png")
    save_image(ero * 255,     "results/10_erosion.png")
    save_image(dil * 255,     "results/11_dilation.png")
    save_image(opn * 255,     "results/12_opening.png")
    save_image(cls * 255,     "results/13_closing.png")

    print("Zrobione. Wyniki w folderze results/")

if __name__ == "__main__":
    main()
