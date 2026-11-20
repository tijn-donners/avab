# Omschrijving van MFEXPORT XML structuur

## <AHD> = Archiefeenheid

Alle <AHD>'s worden op hetzelfde niveau (1 onder <MFEXPORT></mfexport>) geplaatst. Hierarchien tussen AHD's worden bepaald door:

```xml
# verwijst naar de top-level toegang, ook als er meerdere aggeratieniveaus tussen zitten. Deze staat altijd als eerste tag onder de root tag.
<AHD_ID_TOP>6568991</AHD_ID_TOP>  

# verwijst naar de <ID> van de bovenliggende AHD
<AHD_ID>8062999</AHD_ID>
```

## <AWE> = Waarde (bevat NAAM, PROMPT, en WAARDE) Voorbeeld:

```xml
<AWE>
    <NAAM>GEMEENTE</NAAM> 
    <PROMPT>Gemeente</PROMPT>
    <WAARDE>De Bilt</WAARDE>
</AWE>
```

## <AET> = Archiefeenheidsoort. In de XML srtructuur is het een subtag een AHD.

## <SBK> = ? (alleen gebruikt in <INRICHTING></inrichting>)
## <FVD> = Flexveld (alleen gebruikt in <INRICHTING></inrichting>), valt onder SBK
## <TWD> = ? (alleen gebruikt in <INRICHTING></inrichting>)

## <REL> = Relatie? voor info over contextoegangen?
