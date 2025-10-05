from typing import Tuple

# Categories and colors requested:
# Verde, Amarillo, Rojo, Café, Gris
# Estados: cultivo, deforestación, posible cultivo, recuperación, nunca se planto/área verde


def classify_ndvi(ndvi: float) -> Tuple[str, str]:
    if ndvi is None:
        return ("sin_datos", "#808080")  # Gris
    # Typical NDVI interpretation tuned for agriculture (can be refined later)
    if ndvi >= 0.6:
        return ("cultivo", "#2ECC40")  # Verde
    if ndvi >= 0.3:
        return ("posible_cultivo", "#FFDC00")  # Amarillo
    if ndvi >= 0.1:
        return ("recuperacion", "#8E6E53")  # Café
    if ndvi >= 0.0:
        return ("deforestacion", "#FF4136")  # Rojo
    return ("no_plantado_area_verde", "#808080")  # Gris as fallback
