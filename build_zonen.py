"""Erzeugt zonen.json aus den DIBt-Tabellen (Schnee, Wind, Erdbeben).

Regel-Schema (alle Felder optional außer land/zone):
  land      Länderkürzel (BY, NI, ...)
  kreise    Liste Kreisnamen (normalisiert verglichen)
  kf        True = kreisfreie Stadt, False = Landkreis, None = egal
  regbez    Regierungsbezirk / Direktionsbezirk
  ags       8-stelliger Gemeindeschlüssel
  agsp      AGS-Präfix (z. B. 5-stellig für einen Kreis)
  gem       Liste Gemeindenamen
  teil      Gemeindeteil/Ortsteil-Text (Regel gilt nur für Teile der Gemeinde)
  default   True = "alle Gemeinden, soweit nicht ..."
  zone, sk, tiefland, guk, hinweis
"""
import glob, json, re, sys, warnings, collections
import openpyxl
warnings.filterwarnings("ignore")

RAW = sys.argv[1]
OUT = sys.argv[2]


def quelle(name):
    """DIBt-Datei im Ordner RAW finden, auch mit vorangestelltem Präfix im Dateinamen."""
    treffer = sorted(glob.glob(f"{RAW}/*{name}.xlsx"))
    if not treffer:
        sys.exit(f"Datei *{name}.xlsx fehlt in {RAW}")
    return treffer[0]


SCHNEE = quelle("Schneelastzonen_nach_Verwaltungsgrenzen")
WIND = quelle("Windzonen_nach_Verwaltungsgrenzen")
ERDB = quelle("Erdbebenzonen_Formular_Untergrundklassen")


def sheet(wb, prefix):
    return [w for w in wb.worksheets if w.title.strip().startswith(prefix)][0]


def rows(ws):
    return [tuple("" if c is None else c for c in r) for r in ws.iter_rows(values_only=True)]


def s(x):
    return re.sub(r"\s+", " ", str(x)).strip()


def zone(x):
    z = s(x)
    return z.replace(".0", "") if z else ""


def split_names(txt):
    txt = s(txt)
    txt = re.sub(r"^(folgende Gemeinden:|die Gemeinden|die Gemeinde|Gemeinden)\s*", "", txt)
    parts = [p.strip() for p in re.split(r",\s*|\s+und\s+", txt) if p.strip()]
    return parts


def kreis_kf(name):
    """Kreisname bereinigen und erkennen, ob kreisfreie Stadt."""
    n = s(name)
    kf = None
    if re.match(r"^(Stadt|SK|kreisfreie Stadt|Kreisfreie Stadt|Landeshauptstadt)\s", n):
        kf = True
    elif re.match(r"^(LK|Landkreis|Kreis|Region)\s", n) or n.endswith("kreis"):
        kf = False
    n = re.sub(r"^(Stadt|SK|LK|Landkreis|Kreis|kreisfreie Stadt|Kreisfreie Stadt|Region|Landeshauptstadt)\s+", "", n)
    return n.strip(" :"), kf


rules = {"schnee": [], "wind": [], "erdbeben": []}


def add(typ, **r):
    r = {k: v for k, v in r.items() if (v not in (None, "", [], False)) or k == "zone" or (k == "kf" and v is False)}
    rules[typ].append(r)


def tief(txt):
    return bool(re.search(r"tief", s(txt), re.I))


# ------------------------------------------------------------------ Schnee
S = openpyxl.load_workbook(SCHNEE, read_only=True, data_only=True)
BY_HINWEIS = "Bayern: zusätzlich Ergebnisse des Forschungsprojekts zur Schneelast (Rundschreiben StMI 19.01.2018) beachten."

# Tabellen mit Gemeindeschlüssel
for code in ["SH", "HH", "HB", "HE", "RP", "BY", "SL", "BE", "BB", "TH"]:
    for r in rows(sheet(S, code))[1:]:
        if s(r[0]).upper() != code:
            continue
        kreis, ags, gem, z, fn = s(r[1]), s(r[2]), s(r[3]), zone(r[4]), s(r[5])
        if not z:
            continue
        hin = []
        if code == "BY":
            fn = ""
        elif fn and not tief(fn):
            hin.append(fn)
        if ags.lower() == "alle":
            if "außer" in gem:
                hin.append(gem)
            add("schnee", land=code, kreise=[kreis], kf=False, default=True, zone=z,
                tiefland=tief(fn), hinweis=" ".join(hin))
        else:
            add("schnee", land=code, kreise=[kreis] if kreis else None, ags=ags.zfill(8), gem=[gem],
                zone=z, tiefland=tief(fn), hinweis=" ".join(hin))
add("schnee", land="SH", gem=["Helgoland"], zone="1", tiefland=True)

# NRW (Spalten: Kreis, AGS oder Bereich, Gemeinde, Zone)
def nrw(typ, ws):
    for r in rows(ws)[3:]:
        kreis, ags, gem, z = s(r[0]), s(r[1]), s(r[2]), zone(r[3])
        if not kreis or not z:
            continue
        if "bis" in ags:
            ranges = re.findall(r"(\d{7,8})\s*bis\s*(\d{7,8})", ags)
            for a, b in ranges:
                a = a.zfill(8)
                add(typ, land="NW", kreise=[kreis], agsp=a[:5], default=True, zone=z,
                    hinweis=gem if "außer" in gem else None)
        else:
            add(typ, land="NW", kreise=[kreis], ags=ags.replace(".0", "").zfill(8), gem=[gem], zone=z)

nrw("schnee", sheet(S, "NW"))

# Niedersachsen (Kreisebene, Ausnahmen von Hand aus den "außer"-Zeilen)
FN2 = ("Für Gemeinden in Zone 2: Zone 3 ansetzen, wenn das Bauvorhaben nördlich der B 243 "
       "oberhalb der 300-m-Höhenlinie liegt (DIBt-Fußnote 2).")
for r in rows(sheet(S, "NI"))[1:]:
    if s(r[0]).upper() != "NI":
        continue
    k, kf = kreis_kf(r[1])
    z, fn = zone(r[2]), s(r[3])
    add("schnee", land="NI", kreise=[k], kf=kf, default=True, zone=z, tiefland=fn.startswith("1"),
        hinweis=FN2 if fn.startswith("2") else None)
add("schnee", land="NI", kreise=["Hannover"], gem=["Springe", "Wennigsen", "Wennigsen (Deister)"], zone="3")
add("schnee", land="NI", kreise=["Goslar"], gem=["Langelsheim", "Bad Harzburg", "Goslar", "Seesen", "Liebenburg",
    "Lutter am Barenberge", "Lutter"], zone="2", hinweis=FN2)
add("schnee", land="NI", kreise=["Goslar"], gem=["Braunlage"], zone="3", sk=5.5,
    hinweis="Braunlage mit Ortsteilen Königskrug, St. Andreasberg, Sonnenberg, Oderbrück, Oderberg, Hohegeiß: s_k = 5,5 kN/m² (DIBt-Fußnote 3).")
add("schnee", land="NI", kreise=["Goslar"], gem=["Clausthal-Zellerfeld", "Altenau"], teil="Ortsteile Torfhaus und Bastesiedlung (Altenau)",
    zone="3", hinweis="Nur Torfhaus und Bastesiedlung: s_k = 5,5 kN/m², übrige Gemeinde Zone 3.")
add("schnee", land="NI", kreise=["Göttingen"], gem=["Bad Sachsa", "Walkenried", "Wieda", "Zorge"], zone="3")
add("schnee", land="NI", kreise=["Hameln-Pyrmont"], gem=["Bad Münder", "Bad Münder am Deister"], zone="3")

# Baden-Württemberg (Kreis + Gemeindelisten)
regbez = kreis = kf = None
for r in rows(sheet(S, "BW"))[1:]:
    if s(r[0]).upper() != "BW":
        continue
    b, c, z = s(r[1]), s(r[2]), zone(r[3])
    if b.startswith("Regierungsbezirk"):
        regbez = b.replace("Regierungsbezirk", "").strip(" :")
        continue
    if b:
        kreis, kf = kreis_kf(b)
    if not z:
        continue
    if not c or c.lower().startswith("alle gemeinden") and "," not in c.split("sofern")[0]:
        add("schnee", land="BW", regbez=regbez, kreise=[kreis], kf=kf, default=True, zone=z)
        continue
    c = re.sub(r"Alle Gemeinden, sofern nicht.*$", "", c)  # Klebefehler Breisgau-Hochschwarzwald
    teil = None
    if "(" in c:
        teil = c
    names = [re.sub(r"\s*\(.*?\)", "", n) for n in split_names(c)]
    add("schnee", land="BW", regbez=regbez, kreise=[kreis], kf=kf, gem=names, zone=z,
        teil=teil if teil else None)

# Mecklenburg-Vorpommern (von Hand, Tabelle ist Freitext)
MVH = None
add("schnee", land="MV", kreise=["Ludwigslust-Parchim", "Mecklenburgische Seenplatte", "Nordwestmecklenburg"], kf=False, default=True, zone="2", hinweis=MVH)
add("schnee", land="MV", kreise=["Rostock", "Vorpommern-Greifswald"], kf=False, default=True, zone="2", hinweis=MVH)
add("schnee", land="MV", kreise=["Vorpommern-Rügen"], gem=split_names("Dettmannsdorf, Bad Sülze, Tribsees, Lindholz, Deyelsdorf, Grammendorf, Gransebieth, Wendisch Baggendorf, Glewitz, Süderholz"), zone="2", hinweis=MVH)
add("schnee", land="MV", gem=["Neubrandenburg", "Schwerin", "Wismar"], zone="2", hinweis=MVH)
add("schnee", land="MV", kreise=["Rostock"], kf=False, gem=["Börgerende-Rethwisch", "Admannshagen-Bargeshagen", "Nienhagen", "Elmenhorst/Lichtenhagen",
    "Graal-Müritz", "Gelbensande", "Blankenhagen", "Rövershagen", "Mönchhagen", "Bentwisch", "Poppendorf"], zone="3", hinweis=MVH)
add("schnee", land="MV", kreise=["Vorpommern-Rügen"], kf=False, default=True, zone="3", hinweis=MVH)
add("schnee", land="MV", kreise=["Vorpommern-Greifswald"], gem=["Mesekenhagen", "Wackerow", "Neuenkirchen", "Wolgast", "Zemitz", "Lassan", "Buggenhagen",
    "Brünzow", "Hanshagen", "Kemnitz", "Kröslin", "Loissin", "Lubmin", "Neu Boltenhagen", "Rubenow", "Wusterhusen"], zone="3",
    hinweis="Zone 3 außerdem für alle Gemeinden auf der Insel Usedom.")
add("schnee", land="MV", gem=["Greifswald", "Rostock", "Stralsund"], kf=True, zone="3", hinweis=MVH)

# Sachsen-Anhalt
for r in rows(sheet(S, "ST"))[1:]:
    a, b, c, z, fn = s(r[0]), s(r[1]), s(r[2]), zone(r[3]), s(r[4])
    if a == "ST" and z:
        k, _ = kreis_kf(b.replace("Halle (Saale", "Halle (Saale)"))
        teilhin = re.sub(r"^\*Nordd\. Tiefld\.\s*", "", fn)
        hin = ("Norddeutsches Tiefland nur: " + teilhin) if teilhin and tief(fn) else None
        if c.lower() == "alle":
            add("schnee", land="ST", kreise=[k], kf=False, default=True, zone=z, tiefland=tief(fn), hinweis=hin)
        else:
            add("schnee", land="ST", kreise=[k], kf=True, gem=[k], zone=z, tiefland=tief(fn), hinweis=hin)
add("schnee", land="ST", kreise=["Harz"], gem=["Ilsenburg (Harz)", "Ilsenburg"], zone="3",
    hinweis="Ortsteil Darlingerode: Zone 2.")
add("schnee", land="ST", kreise=["Harz"], gem=["Oberharz am Brocken", "Wernigerode"], zone="3")

# Sachsen (Abschnitte je Zone, Gemeindeteile)
z = None
kreis = gem = None
pending = collections.OrderedDict()
for r in rows(sheet(S, "SN")):
    a = s(r[0])
    m = re.match(r"Schneelastzone (\d)", a)
    if m:
        z = m.group(1)
        continue
    if a != "SN":
        continue
    b, c, d = s(r[1]), s(r[2]), s(r[3])
    if b:
        kreis = b
        gem = None
        if not c:
            k, kf = kreis_kf(b)
            add("schnee", land="SN", kreise=[k], kf=kf, default=True, zone=z)
            continue
    if c:
        gem = c
    if not gem:
        continue
    k, kf = kreis_kf(kreis)
    gname = re.sub(r",\s*Stadt.*$", "", gem).strip()
    variants = list(dict.fromkeys([gname, gname.split("/")[0].strip()]))
    if d and re.sub(r",\s*Stadt.*$", "", d).strip() != gname:
        add("schnee", land="SN", kreise=[k], kf=kf, gem=variants, teil=d, zone=z,
            hinweis="Gemeinde liegt in mehreren Zonen – Ortsteil prüfen.")
    else:
        add("schnee", land="SN", kreise=[k], kf=kf, gem=variants, zone=z)

# ------------------------------------------------------------------ Wind (Freitext, von Hand)
def W(land, zone_, **kw):
    add("wind", land=land, zone=str(zone_), **kw)

for land, z in [("HH", 2), ("HE", 1), ("SL", 1), ("BE", 2), ("BB", 2), ("SN", 2), ("ST", 2)]:
    W(land, z, default=True,
      hinweis="Hamburger Hafen: Technische Baubestimmungen Hamburg beachten." if land == "HH" else None)
W("HB", 3, gem=["Bremen"], kf=True)
W("HB", 4, gem=["Bremerhaven"], kf=True)
# SH
W("SH", 3, kreise=["Schleswig-Flensburg", "Flensburg"], default=True)
W("SH", 4, kreise=["Schleswig-Flensburg"], gem=["Wohlde", "Bergenhusen", "Norderstapel", "Süderstapel", "Erfde", "Meggerdorf", "Tielen"])
W("SH", 4, kreise=["Nordfriesland", "Dithmarschen"], default=True)
W("SH", 3, kreise=["Rendsburg-Eckernförde", "Pinneberg", "Steinburg"], default=True)
W("SH", 4, gem=["Helgoland"])
W("SH", 2, kreise=["Segeberg", "Plön", "Stormarn", "Herzogtum Lauenburg", "Kiel", "Lübeck", "Neumünster"], default=True)
W("SH", 2, kreise=["Ostholstein"], default=True)
W("SH", 3, kreise=["Ostholstein"], gem=["Gremersdorf", "Neukirchen", "Heringsdorf", "Göhl", "Grube", "Dahme", "Kellenhusen", "Riepsdorf", "Großenbrode", "Heiligenhafen"])
W("SH", 4, kreise=["Ostholstein"], gem=["Fehmarn"])
# NI
W("NI", 4, kreise=["Aurich", "Wittmund", "Friesland", "Cuxhaven", "Emden", "Wilhelmshaven"], default=True)
W("NI", 3, kreise=["Wesermarsch"], default=True)
W("NI", 4, kreise=["Wesermarsch"], gem=["Nordenham", "Jade", "Ovelgönne", "Brake", "Brake (Unterweser)", "Butjadingen", "Stadland"])
W("NI", 3, kreise=["Stade"], default=True)
W("NI", 4, kreise=["Stade"], gem=["Freiburg", "Freiburg/Elbe", "Balje", "Krummendeich", "Oederquart"])
W("NI", 3, kreise=["Leer", "Ammerland", "Oldenburg", "Osterholz", "Oldenburg (Oldenburg)", "Delmenhorst"], default=True)
W("NI", 4, gem=["Borkum"])
W("NI", 2, kreise=["Rotenburg (Wümme)"], default=True)
W("NI", 3, kreise=["Rotenburg (Wümme)"], gem=["Bremervörde", "Gnarrenburg", "Zeven", "Heeslingen", "Geestequelle", "Selsingen", "Tarmstedt",
    "Oerel", "Alfstedt", "Basdahl", "Ebersdorf", "Hipstedt", "Anderlingen", "Deinstedt", "Farven", "Ostereistedt", "Sandbostel", "Seedorf",
    "Breddorf", "Bülstedt", "Hepstedt", "Kirchtimke", "Tarmstedt", "Vorwerk", "Westertimke", "Wilstedt"],
    hinweis="Samtgemeinden Geestequelle, Selsingen, Tarmstedt mit ihren Mitgliedsgemeinden.")
W("NI", 2, kreise=["Hannover", "Emsland", "Grafschaft Bentheim", "Cloppenburg", "Vechta", "Diepholz", "Verden", "Harburg", "Lüneburg",
    "Heidekreis", "Uelzen", "Lüchow-Dannenberg", "Celle", "Nienburg (Weser)", "Gifhorn", "Peine", "Helmstedt", "Wolfenbüttel", "Goslar",
    "Wolfsburg", "Braunschweig", "Salzgitter"], default=True)
W("NI", 2, kreise=["Osnabrück"], default=True)
W("NI", 1, kreise=["Osnabrück"], gem=["Wallenhorst", "Belm", "Bissendorf", "Melle", "Dissen am Teutoburger Wald", "Bad Iburg",
    "Hilter am Teutoburger Wald", "Georgsmarienhütte", "Hagen am Teutoburger Wald", "Hasbergen", "Osnabrück"])
W("NI", 2, kreise=["Schaumburg"], default=True)
W("NI", 1, kreise=["Schaumburg"], gem=["Rinteln"])
W("NI", 1, kreise=["Hameln-Pyrmont"], default=True)
W("NI", 2, kreise=["Hameln-Pyrmont"], gem=["Bad Münder", "Bad Münder am Deister"])
W("NI", 2, kreise=["Hildesheim"], default=True)
W("NI", 1, kreise=["Hildesheim"], gem=["Duingen", "Alfeld", "Alfeld (Leine)", "Freden", "Freden (Leine)"])
W("NI", 1, kreise=["Holzminden", "Northeim", "Göttingen"], default=True)
W("NI", 2, kreise=["Göttingen", "Northeim", "Holzminden"], gem=["Bad Grund (Harz)", "Bad Grund", "Bad Lauterberg im Harz", "Bad Sachsa",
    "Herzberg am Harz", "Osterode am Harz", "Walkenried", "Hattorf am Harz", "Elbingerode", "Hörden am Harz", "Wulften am Harz"],
    hinweis="Samtgemeinde Hattorf mit Mitgliedsgemeinden.")
# NW
nrw("wind", sheet(openpyxl.load_workbook(WIND, read_only=True, data_only=True), "NW"))
# RP
W("RP", 1, default=True)
W("RP", 2, kreise=["Ahrweiler", "Vulkaneifel", "Bitburg-Prüm", "Eifelkreis Bitburg-Prüm"], default=True)
W("RP", 2, kreise=["Cochem-Zell", "Bernkastel-Wittlich", "Trier-Saarburg", "Trier", "Mayen-Koblenz", "Koblenz"], default=True,
  hinweis="Gemeinden und Gemeindeteile rechts der Mosel (bei Mayen-Koblenz/Koblenz auch rechts des Rheins) liegen in Windzone 1.")
# BW
W("BW", 1, default=True)
W("BW", 1, kreise=["Konstanz"], default=True,
  hinweis="Bodensee und Anrainergemeinden bis 3 km landeinwärts: Windzone 2 – Abstand zum Ufer prüfen.")
W("BW", 1, kreise=["Alb-Donau-Kreis", "Alb-Donau"], default=True)
W("BW", 2, kreise=["Alb-Donau-Kreis", "Alb-Donau"], gem=["Balzheim", "Dietenheim", "Hüttisheim", "Illerkirchberg", "Illerrieden", "Schnürpflingen", "Staig"])
W("BW", 2, kreise=["Bodenseekreis", "Biberach", "Ravensburg", "Sigmaringen"], default=True)
# BY
W("BY", 1, default=True)
W("BY", 2, kreise=["Günzburg", "Neu-Ulm", "Augsburg", "Aichach-Friedberg", "Unterallgäu", "Lindau (Bodensee)", "Lindau", "Memmingen", "Kaufbeuren"], default=True)
W("BY", 1, kreise=["Oberallgäu"], default=True)
W("BY", 2, kreise=["Oberallgäu"], gem=["Altusried", "Dietmannsried", "Haldenwang"])
W("BY", 2, kreise=["Ostallgäu"], default=True)
W("BY", 1, kreise=["Ostallgäu"], gem=split_names("Pfronten, Hopferau, Nesselwang, Füssen, Schwangau, Rieden am Forggensee, Roßhaupten, Seeg, Görisried, Wald, Lengenwang, Stötten a. Auerberg, Rückholz, Eisenberg, Lechbruck, Halblech")
  + ["Stötten am Auerberg", "Lechbruck am See"])
W("BY", 2, kreise=["Dachau", "München", "Fürstenfeldbruck", "Landsberg am Lech", "Ebersberg", "Starnberg", "Rosenheim"], default=True,
  hinweis="Gilt für Landkreis und Landeshauptstadt München sowie die kreisfreie Stadt Rosenheim.")
W("BY", 2, kreise=["Weilheim-Schongau"], default=True)
W("BY", 1, kreise=["Weilheim-Schongau"], gem=["Steingaden", "Prem", "Wildsteig", "Bernbeuren"], hinweis="Verwaltungsgemeinschaft Steingaden und Gemeinde Bernbeuren.")
W("BY", 1, kreise=["Bad Tölz-Wolfratshausen"], default=True)
W("BY", 2, kreise=["Bad Tölz-Wolfratshausen"], gem=split_names("Wolfratshausen, Icking, Münsing, Egling, Geretsried, Eurasburg, Königsdorf, Bad Tölz, Reichersbeuern, Dietramszell, Bad Heilbrunn, Sachsenkam"))
W("BY", 1, kreise=["Miesbach"], default=True)
W("BY", 2, kreise=["Miesbach"], gem=split_names("Holzkirchen, Otterfing, Warngau, Valley, Weyarn, Irschenberg, Miesbach, Gmund a. Tegernsee, Waakirchen, Hausham") + ["Gmund am Tegernsee"])
W("BY", 2, kreise=["Traunstein"], default=True)
W("BY", 1, kreise=["Traunstein"], gem=split_names("Grassau, Schleching, Staudach-Egerndach, Marquartstein, Unterwössen, Reit im Winkl, Ruhpolding, Bergen, Siegsdorf, Inzell, Surberg, Petting, Wonneberg, Waging a. See, Kirchanschöring, Fridolfing, Taching a. See, Palling, Tittmoning, Engelsberg, Tacherting")
  + ["Waging am See", "Taching am See"])
W("BY", 2, kreise=["Rosenheim"], kf=False, default=True)
W("BY", 1, kreise=["Rosenheim"], kf=False, gem=split_names("Kiefersfelden, Oberaudorf, Flintsbach a.Inn, Brannenburg, Nußdorf a.Inn, Samerberg, Aschau i.Chiemgau")
  + ["Flintsbach am Inn", "Nußdorf am Inn", "Aschau im Chiemgau"])
# MV
W("MV", 2, kreise=["Ludwigslust-Parchim", "Mecklenburgische Seenplatte", "Vorpommern-Greifswald"], default=True)
W("MV", 3, kreise=["Nordwestmecklenburg", "Rostock"], kf=False, default=True)
W("MV", 2, kreise=["Nordwestmecklenburg"], gem=["Gadebusch", "Dragun", "Kneese", "Krembz", "Mühlen Eichsen", "Roggendorf", "Rögnitz", "Veelböken",
    "Lützow", "Lübstorf", "Alt Meteln", "Brüsewitz", "Cramonshagen", "Dalberg-Wendelstorf", "Gottesgabe", "Grambow", "Klein Trebbow", "Pingelshagen",
    "Pokrent", "Schildetal", "Seehof", "Zickhusen"], hinweis="Ämter Gadebusch und Lützow-Lübstorf (Mitgliedsgemeinden prüfen).")
W("MV", 2, kreise=["Rostock"], kf=False, default=False, gem=["Bützow", "Güstrow", "Laage", "Krakow am See", "Gnoien", "Teterow"],
  hinweis="Windzone 2 für alle Gemeinden der Ämter Bützow-Land, Güstrow-Land, Laage, Krakow am See, Mecklenburgische Schweiz und Gnoien – Amtszugehörigkeit prüfen.")
W("MV", 2, gem=["Greifswald", "Güstrow", "Neubrandenburg", "Schwerin", "Teterow"])
W("MV", 3, kreise=["Vorpommern-Rügen"], default=True)
W("MV", 3, gem=["Rostock", "Stralsund", "Wismar"])
W("MV", 4, kreise=["Vorpommern-Rügen"], gem=["Insel Hiddensee", "Hiddensee", "Bergen auf Rügen"],
  hinweis="Windzone 4 für die Ämter West-Rügen (inkl. Hiddensee), Nord-Rügen und Bergen auf Rügen außer Gustow, Poseritz, Garz/Rügen – Amtszugehörigkeit prüfen.")
# TH
W("TH", 2, default=True)
W("TH", 1, kreise=["Schmalkalden-Meiningen", "Hildburghausen", "Sonneberg", "Suhl"], default=True)
W("TH", 1, kreise=["Wartburgkreis", "Wartburg"], default=True)
W("TH", 2, kreise=["Wartburgkreis", "Wartburg"], gem=split_names("Behringen, Berka v.d. Hainich, Creuzburg, Falken, Großenlipnitz, Ifta, Mihla, Nazza, Reichenbach, Ruhla, Schnellmannshausen, Treffurt, Tüngeda, Wutha-Farnroda")
  + ["Amt Creuzburg", "Hörselberg-Hainich"], hinweis="Gebietsstand 2022 – Gemeindefusionen beachten.")

# Regierungsbezirk-Regeln Bayern (alles außer Schwaben/Oberbayern = 1) sind durch default=1 abgedeckt.
# Schwaben-Kreise mit Windzone 1 (Donau-Ries, Dillingen, Kempten) und Oberbayern 9.7.1 = default 1.

# ------------------------------------------------------------------ Erdbeben
E = openpyxl.load_workbook(ERDB, read_only=True, data_only=True)
AGR = {"0": None, "1": 0.4, "2": 0.6, "3": 0.8}


def agg(land, key, kreis, gem, items, by_ags=True):
    """items: Liste (zone, guk, gemarkung). Zone 99/k.A. = keine Erdbebenzone."""
    zs = [(z, g, m) for z, g, m in items]
    real = [x for x in zs if x[0] not in ("99", "", "k. A.")]
    if not real:
        zmax, guk = "–", ""
    else:
        zmax = max(real, key=lambda x: int(x[0]))[0]
        guk = "/".join(sorted({x[1] for x in real if x[1] and x[0] == zmax}))
    distinct = sorted({x[0] for x in zs})
    hin = None
    if len(distinct) > 1:
        parts = collections.defaultdict(list)
        for z, g, m in zs:
            if m:
                parts["keine Erdbebenzone" if z in ("99", "", "k. A.") else "Zone " + z].append(m)
        hin = "Gemarkungsabhängig: " + "; ".join(f"{k}: {', '.join(sorted(set(v)))[:180]}" for k, v in sorted(parts.items()))
    r = dict(land=land, gem=[gem], zone=zmax, guk=guk, hinweis=hin)
    if by_ags:
        r["ags"] = key
    if kreis:
        r["kreise"] = [kreis]
    add("erdbeben", **r)


for land, name in [("BY", "Bayern"), ("RP", "Rheinland-Pfalz")]:
    g = collections.OrderedDict()
    for r in rows(E[name])[1:]:
        if not isinstance(r[2], (int, float)) or r[6] == "":
            continue
        ags = str(int(r[2])).zfill(8)
        g.setdefault(ags, [s(r[1]), s(r[3]), []])[2].append((zone(r[6]), s(r[7]), s(r[5])))
    for ags, (k, gem, items) in g.items():
        agg(land, ags, k, gem, items)

g = collections.OrderedDict()
for r in rows(E["Hessen"])[1:]:
    if not r[4]:
        continue
    ags = "06" + str(int(r[4])).zfill(6)
    z = s(r[2]).replace("Zone ", "")
    gk = s(r[3]).replace("Untergrundklasse ", "")
    g.setdefault(ags, [kreis_kf(r[7])[0], s(r[5]), []])[2].append(("k. A." if "A." in z else z, "" if "A." in gk else gk, s(r[1])))
for ags, (k, gem, items) in g.items():
    agg("HE", ags, k, gem, items)

g = collections.OrderedDict()
for r in rows(E["Thüringen"])[2:]:
    if r[0] and r[3] != "":
        g.setdefault(s(r[0]), []).append((zone(r[3]), s(r[4]), s(r[2])))
for gem, items in g.items():
    agg("TH", None, None, gem, items, by_ags=False)

g = collections.OrderedDict()
for r in rows(E["Sachsen-Anhalt"]):
    if r[0] and isinstance(r[2], (int, float)):
        g.setdefault(s(r[0]), []).append((zone(r[2]), s(r[3]), s(r[1])))
for gem, items in g.items():
    agg("ST", None, None, gem, items, by_ags=False)

g = collections.OrderedDict()
kreis = gem = guk = None
for r in rows(E["Sachsen"])[1:]:
    a, b, c, z, gk = s(r[0]), s(r[1]), s(r[2]), zone(r[3]), s(r[4])
    if not z:
        continue
    if a:
        kreis = kreis_kf(a.replace("Mitttel", "Mittel"))[0]
    if b:
        gem = re.sub(r",\s*Stadt.*$", "", b).strip()
    if gk:
        guk = gk
    g.setdefault((kreis, gem), []).append((z, guk, c or gem))
for (k, gem), items in g.items():
    agg("SN", None, k, gem, items, by_ags=False)

LAND_HINWEIS = {
    "schnee": {
        "BY": BY_HINWEIS,
        "RP": "Rheinland-Pfalz: Exklaven der ausgewiesenen Gemeinden liegen in Schneelastzone 2.",
        "MV": "Mecklenburg-Vorpommern: Anlage A 1.2.1/4 der VV TB M-V (Erlass vom 05.01.2023) beachten.",
        "NI": "Niedersachsen: Sonderregelungen im Harz beachten.",
        "SN": "Sachsen: Zuordnung nach Anhang A der VwV TB Sachsen.",
    },
    "wind": {
        "MV": "Mecklenburg-Vorpommern: Zuordnung teils nach Amtsbereichen – Amtszugehörigkeit prüfen.",
    },
    "erdbeben": {
        "BW": "Baden-Württemberg: Zuordnung nur über die Karte der Erdbebenzonen 1:350 000 (LGL BW).",
        "NW": "NRW: Zuordnung über die Erdbebenzonenkarte des Geologischen Dienstes NRW.",
        "ST": "Gemeinde nicht in der Tabelle: keine Erdbebenzone bzw. Zone 0.",
        "_ohne": "Für dieses Land enthält die DIBt-Tabelle keine Erdbebenzonen.",
        "_fehlt": "Gemeinde nicht in der Tabelle: keine Erdbebenzone bzw. Zone 0.",
    }
}

out = {
    "stand": {"schnee": "DIBt 07.02.2023", "wind": "DIBt 02.06.2022", "erdbeben": "DIBt 02.06.2022"},
    "agR": AGR,
    "landHinweis": LAND_HINWEIS,
    **rules,
}
json.dump(out, open(OUT, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, separators=(",", ":"))
print({k: len(v) for k, v in rules.items()})
