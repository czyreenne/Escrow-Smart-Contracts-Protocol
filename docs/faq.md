# Frequently Asked Questions (FAQ)

**Q: What blockchain is this deployed on?**  
A: Sepolia Ethereum testnet.

**Q: How does the auto-refund work?**  
A: After the timeout, only the buyer can call `refund()`, returning all funds if not already released.

**Q: How do you prevent reentrancy attacks?**  
A: By updating state before external calls and avoiding functions like call/value/transfer wherever possible.

**Q: Can this protocol be upgraded?**  
A: The MVP has no upgrade path; future versions may use proxy or modular patterns.

See [overview.md](overview.md) for background.
