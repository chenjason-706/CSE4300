/* These programs are built without the C library (-nostdlib) so the trace
   only has our own code's memory accesses, not hundreds of thousands of
   accesses from libc starting up. */

static unsigned int seed = 12345;

static unsigned int next_random(void) {
    seed = seed * 1103515245u + 12345u;
    return seed >> 8;
}

static void exit_program(long code) {
    __asm__ volatile("mov $60, %%eax\n syscall" : : "D"(code) : "rax", "rcx", "r11", "memory");
    __builtin_unreachable();
}

int main(void);

void _start(void) {
    exit_program(main());
}
