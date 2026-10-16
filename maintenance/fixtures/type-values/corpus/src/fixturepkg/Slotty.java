package fixturepkg;

// A registry keyed "Slot", which is ALSO an ordinary field in the shipped assets (see
// assets/Server/Thing/slots.json): a MIXED key. Its registered name is CONFIRMED where a doc uses
// it; any other value under "Slot" is UNCHECKED, never a failure.
public class Slotty {
    public static final CodecMapCodec<Slotty> CODEC = new CodecMapCodec("Slot");

    public static void setup() {
        Slotty.CODEC.register("Core2", CoreSlotty.class, CoreSlotty.CODEC);
    }
}
