#!/usr/bin/env python3

import itertools
import json
import lxml.etree
import re


def intensity2rgb(x):
    if args.cl == 0:
        x *= 4/5; # Avoid pure white and pure black (hard to see)
        return (x**2 / 2**0.5,  x**2 / 2**0.5,  0)
    if args.cl == 1:
        return ((1 - x)**2 / 2**0.5,  x**2 / 2**0.5,  x**2 / 2**0.5)
    if args.cl == 2:
        return ((1 - x)**2,  0,  x**2)
    raise ValueError(f"Invalid colour scheme: {args.cl}")

def rgb2hex(tpl):
    return rgb2hex_255([int(255*x) for x in tpl])

def rgb2hex_255(tpl):
    return "#{:02X}{:02X}{:02X}".format(*tpl)

def ls_overlap(*ls):
    for A,B in itertools.combinations(ls, 2):
        overlap = [x for x in A if x in B]
        if len(overlap) > 0:
            return overlap

def rtree(node, fnct):
    for child in node:
        rtree(child, fnct)
    fnct(node)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    
    parser_inputs = parser.add_mutually_exclusive_group(required=True)
    parser_inputs.add_argument('--csv', help="Path to 'csv' data file of country to value, where entries are delineated by commas")
    parser_inputs.add_argument('--txt', help="Path to text file of countries, whose values will be entered interactively")
    
    parser.add_argument("--cl", type=int, default=1)
    
    parser.add_argument('--write-template', help='[Debug tool] Write template country2rgb.csv to the specified path')
    
    parser.add_argument('--out', required=True, help='Path to resulting SVG image file')

    parser.add_argument("--ignore", "-i", action="store_true", default=False, help="Warn, rather than fail, on errors")

    args = parser.parse_args()
    
    # Test colour scheme
    intensity2rgb(0)

    try:
        country_codes = re.findall('<(g|path)[^>]* id="([a-z]{2})"[^>]*>(\n *)?<title.*\n *id=[^>]+>([^<]+)<', open("res/BlankMap-World-Microstates.svg").read())
    except FileNotFoundError:
        raise Exception("Please download 'https://commons.wikimedia.org/wiki/File:BlankMap-World-Microstates.svg' and save it under the 'res' folder")
    
    country_codes = [(x[1], x[3]) for x in country_codes]
    # country_codes += [("no","Norway"), ("fi","Finland"), ("gr","Greece"), ("es","Spain")] # Has no effect. Map is bad and needs editing. TODO: Check licensing of map etc. and prepare for it to become part of repo.

    country2code = {y:x for x,y in country_codes}
    code2country = {x:y for x,y in country_codes}
    
    nickname2country = {}
    for tpl in [x.split('\t') for x in open('data/nicknames.csv').read().split('\n') if x != ""]:
        for nickname in tpl:
            nickname2country[nickname] = tpl[0]
    
    if args.write_template:
        with open(args.write_template, 'w') as f:
            for code,name in sorted(country_codes, key=lambda x: x[1]):
                f.write(f"{name}\t\n")
        exit()
    elif args.txt is None:
        country2intensities = [x.split('\t') for x in open(args.csv).read().split('\n') if x != "" and x[0] != ""]
        _values:list = [float(y) for _, y in country2intensities]
        _max:int = max(_values)
        _min:int = min(_values)
        country2intensity   = {nickname2country.get(x, x):(float(y) - _min)/(_max - _min) for x,y in country2intensities}
    else:
        country2intensity = {}
        with open("country2intensity.backup.csv", "w") as f:
            for country in open(args.txt).read().split('\n'):
                if country == "":
                    continue
                s = input(f"{country}: ")
                if s == "":
                    continue
                country2intensity[country] = float(s)
                f.write(f"{country}\t{s}\n")
    
    code2rgb:dict = {}
    for country_name, country_intensity in country2intensity.items():
        if country_name not in country2code:
            if args.ignore:
                print(f"No country code for: {country_name}")
                continue
            raise Exception(f"No country code for: {country_name}")
        code2rgb[country2code[country_name]] = intensity2rgb(country_intensity)

    tree = lxml.etree.parse('res/BlankMap-World-Microstates.svg')
    root = tree.getroot()
    
    for child in root:
        ID = child.attrib['id']
        if len(ID) != 2:
            classes = child.attrib.get('class', [])
            ID = ls_overlap(classes,country2code.values())
        try:
            rgb = code2rgb[ID]
            countryname = code2country.get(ID, '?')
            print(ID, countryname)
            def restyle(gchild):
                oldstyle = gchild.attrib.get('style', None)
                if oldstyle is not None:
                    print("", oldstyle)
                    gchild.attrib['style'] = re.sub('fill:#[0-9a-f]{6}', 'fill:'+rgb2hex(rgb), oldstyle)
            rtree(child,restyle)
        except KeyError:
            pass
    
    tree.write(args.out)
