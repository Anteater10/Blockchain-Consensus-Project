from paxos.state import PaxosNodeState
from paxos.instance import PaxosInstance
from paxos.messages import PaxosMessage, PaxosMessageType

state = PaxosNodeState(node_id=1)

inst = PaxosInstance(
    depth=0,
    node_state=state,
    peers=[2, 3, 4, 5],
    send_func=lambda peer, msg: print("send->", peer, msg.to_dict()),
    broadcast_func=lambda msg: print("broadcast->", msg.to_dict()),
    on_decide=lambda depth, val: print("decided:", depth, val),
)

inst.start_proposal("hello")

msg = PaxosMessage(
    type=PaxosMessageType.PREPARE,
    from_id=2,
    ballot=(1, 2, 0),
    depth=0,
)

inst.handle_message(msg)
