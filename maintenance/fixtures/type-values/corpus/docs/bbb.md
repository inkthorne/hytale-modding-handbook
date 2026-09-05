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

3. `Theta` is waived on this page and appears on no other, so it is the one value
   the **skiplist bucket** actually claims. Without it that bucket reads 0 in every
   case and the one source whose job is waiving goes untested:

   ```json
   { "Type": "Theta" }
   ```
