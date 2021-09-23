# Usage

## JOSM layer preparation
1) Add new layer in JOSM and draw ways you want to walk through

![Initial layer](img/path.png)

2) Select start node and tag it as `start=yes`
3) Select end node and tag it as `end=yes` 
4) If you want to mark some of the route parts as optional, you can mark way by
adding tag `optional=yes`. Keep in mind that this is very expensive operation,
the complexity currently is 2^N for N optional ways. It will try all combinations
of ways and choose the shortest one.
5) Save layer to osm file

## Usage

1) Run 
```
python solver.py <osmfile> <gpxfile>
```
where 
 - *osmfile* is path to osm file saved on step 4 of previous section
 - *csvfile* is path to output gpx file to produce
