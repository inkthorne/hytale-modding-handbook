package fixture;
class Registry {
    void register() {
        a.setPath("Item/Items"); b.setPath("Item/Interactions"); c.setPath("Audio/SoundEvents");
        d.setPath("Entity/Effects"); e.setPath("Particles"); f.setPath("Drops");
        g.setPath("Item/Block/Spawners");
        h.setPath("Missing/Store");   // declared by the jar, absent from this build
    }
}
