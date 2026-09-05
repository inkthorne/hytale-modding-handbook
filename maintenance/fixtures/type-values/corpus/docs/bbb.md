# Page B

`Epsilon` appears here too, but this page does NOT register it — it is waived by
the fixture skiplist instead. That makes `Epsilon` a value resolved by DIFFERENT
sources on different pages, which is the case the tally used to get wrong.

1. Indented fence, nested in a list — guards the FENCE anchor:

   ```json
   { "Type": "Epsilon" }
   ```

2. And a plain one:

   ```json
   { "Type": "Beta" }
   ```
