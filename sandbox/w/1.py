"""
模块1：状态机与决策引擎（拒绝死循环）
实现带超时和强制中断的 Workflow，防止 THINK ↔ ACT 无限循环。
当完整闭环（THINK -> ACT -> THINK）达到 5 次时，强制转入 FINISH 并输出终止信息。
"""

from enum import Enum
from typing import Any, Callable, Dict, Optional


class WorkflowState(Enum):
    START = "start"
    THINK = "think"
    ACT = "act"
    FINISH = "finish"


class DecisionEngine:
    """决策引擎：管理状态转换、循环计数器，并强制终止循环超限的任务。"""

    def __init__(self, max_loops: int = 5):
        """
        :param max_loops: 允许的最大 THINK->ACT->THINK 闭环次数，超限则强制终止
        """
        self.max_loops = max_loops
        self.reset()

    def reset(self) -> None:
        """重置引擎状态，准备处理新任务。"""
        self.counter = 0
        self.state = WorkflowState.START
        self.prev_state = None
        self.terminated = False
        self.final_message = None

    def step(self, think_fn: Callable[[], str], act_fn: Callable[[], Any]) -> Dict[str, Any]:
        """
        执行一步状态转换。

        :param think_fn: 无参数，返回 'act' 或 'finish'，表示下一步动作。
        :param act_fn: 无参数，执行外部动作并返回结果（可忽略）。
        :return: 包含当前状态、输出信息和终止标志的字典。
        """
        if self.terminated or self.state == WorkflowState.FINISH:
            return {
                "state": WorkflowState.FINISH,
                "output": self.final_message or "任务已终止",
                "terminated": True,
            }

        # ---------- START ----------
        if self.state == WorkflowState.START:
            self.state = WorkflowState.THINK
            self.prev_state = WorkflowState.START
            return {"state": self.state, "output": None, "terminated": False}

        # ---------- THINK ----------
        if self.state == WorkflowState.THINK:
            decision = think_fn()
            if decision == "act":
                self.state = WorkflowState.ACT
                self.prev_state = WorkflowState.THINK  # 记录进入 ACT 前的状态为 THINK
                return {"state": self.state, "output": None, "terminated": False}
            else:  # decision == "finish"
                self.state = WorkflowState.FINISH
                self.final_message = "任务完成"
                return {"state": self.state, "output": "任务完成", "terminated": True}

        # ---------- ACT ----------
        if self.state == WorkflowState.ACT:
            result = act_fn()
            # 行动后总是回到 THINK
            self.state = WorkflowState.THINK

            # 检测是否完成了一个完整闭环：上一次状态是 THINK，且现在回到 THINK
            if self.prev_state == WorkflowState.THINK:
                self.counter += 1
                if self.counter >= self.max_loops:
                    self.terminated = True
                    self.state = WorkflowState.FINISH
                    self.final_message = "任务过于复杂，已终止"
                    return {
                        "state": self.state,
                        "output": self.final_message,
                        "terminated": True,
                    }

            self.prev_state = WorkflowState.ACT  # 记录刚刚执行了 ACT
            return {"state": self.state, "output": result, "terminated": False}

        # 未预期的状态
        self.state = WorkflowState.FINISH
        self.final_message = "未知错误"
        return {"state": self.state, "output": "未知错误", "terminated": True}

    def run(self, think_fn: Callable[[], str], act_fn: Callable[[], Any]) -> Dict[str, Any]:
        """
        循环执行 step，直到状态机终止。
        返回最终输出信息。
        """
        self.reset()
        while not self.terminated and self.state != WorkflowState.FINISH:
            step_result = self.step(think_fn, act_fn)
            # 可以打印调试信息
            print(f"[状态] {step_result['state'].value}, 计数器: {self.counter}, 输出: {step_result.get('output')}")
        # 返回最终输出
        return {"final_output": self.final_message, "counter": self.counter}


# ============= 模拟测试 =============

def create_mock_functions():
    """
    创建模拟的 think 和 act 函数，模拟反复思考/行动。
    我们让前 5 次闭环都返回 'act'，第 6 次才返回 'finish'，
    但由于引擎在第五次闭环后强制终止，所以永远看不到第 6 次。
    这模拟了用户输入“请计算1+1，然后告诉我天气，再重复一遍1+1”时模型反复处理子任务。
    """
    # 使用闭包记录调用次数，确保每个闭环的 think 调用都被计数
    think_call_count = 0
    act_call_count = 0

    def think_fn() -> str:
        nonlocal think_call_count
        think_call_count += 1
        # 总是返回 'act'，模拟模型认为需要继续行动（除非达到阈值被强制终止）
        # 如果希望模拟自然完成，可在一定次数后返回 'finish'，但这里我们让它永远 act，
        # 从而触发强制终止。
        return "act"

    def act_fn() -> str:
        nonlocal act_call_count
        act_call_count += 1
        # 模拟执行动作，返回一些结果
        if act_call_count == 1:
            return "计算结果：2"
        elif act_call_count == 2:
            return "天气：晴，25°C"
        elif act_call_count == 3:
            return "再次计算：1+1=2"
        elif act_call_count == 4:
            return "再确认天气：晴"
        else:
            return "重复动作..."

    return think_fn, act_fn


def main():
    """运行测试用例：输入“请计算1+1，然后告诉我天气，再重复一遍1+1”。"""
    print("=== 测试：状态机拒绝死循环 ===\n")
    engine = DecisionEngine(max_loops=5)
    think_fn, act_fn = create_mock_functions()

    # 运行工作流
    result = engine.run(think_fn, act_fn)
    print(f"\n最终结果: {result['final_output']}")
    print(f"总闭环次数: {result['counter']}")


if __name__ == "__main__":
    main()