# Högerklicksmeny för POI-rader

## Ny funktionalitet
Nu kan du högerklicka på valfri POI-rad i **huvudfönstret** för att få upp en kontextmeny med snabbalternativ.

## Tillgängliga alternativ i menyn:

### 1. Aktivera/Avaktivera POI
- **Aktivera POI** / **Avaktivera POI** - Växlar POI:ns aktiva status (samma som checkboxen)

### 2. Kopiera-funktioner
- **Kopiera koordinater** - Kopierar lat, lon till urklipp (format: "lat, lon") - endast om POI har koordinater
- **Kopiera systemnamn** - Kopierar endast systemnamnet
- **Kopiera body-namn** - Kopierar fullständiga body-namnet (system + body)

### 3. Åtgärder
- **Redigera** - Öppnar redigeringsdialogen för POI:n
- **Dela länk** - Kopierar delningslänk till urklipp
- **Flytta POI** - Öppnar dialogen för att flytta POI till annan mapp
- **Ta bort POI** - Tar bort POI:n med bekräftelsedialog

## Hur man använder
1. Högerklicka på valfri POI-rad i huvudfönstret (antingen på checkboxen eller på beskrivningstexten)
2. Välj önskat alternativ från menyn
3. Funktionen körs omedelbart (utom för "Ta bort" som kräver bekräftelse)

## Förändring i huvudfönstret
- **☰-menyn** visar nu endast POI-namn som disabled items (du kan inte klicka på dem)
- För att interagera med POI:er: **högerklicka direkt på POI-raden** i huvudfönstret
- Detta gör huvudfönstret renare och actions lättare att komma åt

## Var fungerar det?
- **När du är på en planet**: POI:er visas med checkbox och beskrivning - högerklicka på någon av dem
- **När du är i ett system (men inte på planet)**: POI:er visas som "Body - Beskrivning" - högerklicka på texten

## Tekniska detaljer
- Context-menyn är bunden till både checkbox och beskrivnings-label
- Använder samma funktioner som hamburgermenyn och settings
- Översättningar finns för både engelska och svenska
- Fungerar med tema-stöd via EDMC:s `theme.update()`

## Testing
Efter att ha startat om EDMC:
1. Landa på en planet med sparade POI:er
2. Högerklicka på någon av POI-raderna i huvudfönstret
3. Testa de olika alternativen i menyn
