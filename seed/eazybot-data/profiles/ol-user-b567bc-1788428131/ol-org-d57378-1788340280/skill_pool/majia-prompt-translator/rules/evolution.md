positioning:
  进化靠对话约定实现。
  用户通过固定句式告诉系统新偏好，系统通过上下文推测用户习惯，纯对话驱动。

signal_satisfied:
  trigger: 记住、保存、收藏、很好、完美、就是这个、就这个、用这个、出吧
  action: 视为满意，提取偏好设置，告知用户已记住偏好

signal_dissatisfied:
  trigger: 不对、不是、完全不是、重来、改掉、删掉、不要这个
  action: 视为不满意，识别冲突偏好，告知用户已记录下次避免

signal_implicit_satisfied:
  trigger: 谢谢、好、可以、行、发出去了
  action: 提取本次成功的生成模式，告知用户成功案例已收录

signal_skip:
  trigger: 以上均不满足
  action: 静默跳过

evolution_action:
  store_preference: 提取本次生成偏好，告知用户已记住
  store_case: 提取本次成功模式，告知越用越懂你
  forget: 识别冲突偏好，告知下次避免
  error: 任何步骤失败均静默跳过，不影响主任务

user_convention:
  submit_preference:
    句式: 偏好：[描述]、记住：[内容]
    示例: 偏好：简洁专业，少用感叹号
  submit_case:
    句式: 这个很好，记住
    action: 自动捕获上下文作为案例
  forget:
    句式: 忘掉XX偏好、不要XX风格
    示例: 忘掉上次的口语风格

research_integration:
  调研时加载用户偏好档案
  优先推荐常用领域
  将已知偏好融入选项并标记推荐

effect:
  更少返工: 系统自动融入已知偏好，首次输出更贴合
  更准调研: 调研时优先推荐用户常用的领域和风格
  越说越懂: 无需重复描述相同偏好，系统自动记住
