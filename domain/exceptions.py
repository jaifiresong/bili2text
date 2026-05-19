class DomainException(Exception):
    """领域异常基类。

    所有业务级别的异常都应继承此类，以便 presentation 层统一捕获并映射为 HTTP 状态码。
    """
    pass


class InvalidVideoUrlError(DomainException):
    """视频 URL 格式无效或不符合预期规则时抛出（HTTP 400）。"""
    pass


class TaskNotFoundError(DomainException):
    """按 ID 查询任务不存在时抛出（HTTP 404）。"""
    pass


class TaskAlreadyProcessingError(DomainException):
    """任务已被提交且正在处理中时抛出（HTTP 409）。"""
    pass
