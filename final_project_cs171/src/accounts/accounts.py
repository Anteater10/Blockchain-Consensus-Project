# src/accounts/accounts.py

# this file keeps track of balances for each client
# uses a list of all clients in the system

CLIENT_IDS = ["P1", "P2", "P3", "P4", "P5"]
INITIAL_BALANCE = 100  # starting money for each client

class AccountsTable:
    def __init__(self, balances=None):
        if balances is None:
            balances = {}
        self.balances = balances

    def fresh():
        """
        Create a new AccountsTable where every client starts with INITIAL_BALANCE.
        (Called as AccountsTable.fresh())
        """
        balances = {}
        for cid in CLIENT_IDS:
            balances[cid] = INITIAL_BALANCE
        return AccountsTable(balances)

    def can_debit(self, client_id, amount):
        current = self.balances.get(client_id, 0)
        return current >= amount

    def apply_transaction(self, tx):
        sender, receiver, amount = tx

        if not self.can_debit(sender, amount):
            print(f"[ACCOUNTS] insufficient funds for {sender} (tried to send {amount})")
            raise ValueError(f"Insufficient funds for {sender}")

        self.balances[sender] -= amount
        if receiver not in self.balances:
            self.balances[receiver] = 0
        self.balances[receiver] += amount
