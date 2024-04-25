#!/usr/bin/env python3

def hex_to_rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))


def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb


def rgb_to_greyscal(rgb):
    r, g, b = rgb
    gr = int(r * 0.299 + g * 0.587 + b * 0.114)
    return (gr, gr, gr)


while True:
    hex = input("Enter hex colour: ")
    if not hex:
        break

    rgb = hex_to_rgb(hex)
    grgb  = rgb_to_greyscal(rgb)
    print(rgb_to_hex(grgb))