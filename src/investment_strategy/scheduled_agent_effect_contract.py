YªçŠx-®éÜj×¢ëiºÚ+Š§j[h‘éÜ¢éíÛž=N‹Z–‹­¦ëeŠw¬Ôˆˆ‰Ñ¥½¸µÍ½Á•‘ÕÉ…‰±”µ•™™•Ð…¹½¹Í•ÅÕ•¹”…Á…‰¥±¥Ñ¥•Ì¸()Q¡”Ñ¥½¸½I•ÍÕ±ÐÉ…Á ¥ÌÑ¡”•á•ÕÑ…‰±”Ñ½Á½±½ä¸€Q¡¥Ìµ½‘Õ±”¥ÌÑ¡”½¹”)É•Á½Í¥Ñ½Éäµ½Ý¹•Ñ…‰±”Ñ¡…Ð‘•ÍÉ¥‰•ÌÝ¡…Ð„±•…°ÑÉ…¹Í¥Ñ¥½¸µÕÍÐ±•…Ù”)‰•¡¥¹¸€%Ð¥¹Ñ•¹Ñ¥½¹…±±ä‘•ÍÉ¥‰•Ì…™™¥Éµ…Ñ¥Ù”•Ù¥‘•¹”Ñ…É•ÑÌ…¹Ñ¡”)¹•áÐµ¥ÍÍ¥¹œ•›møöÚ$z{-®éÜj×ction: str) -> frozenset[str]:
    try:
        return _ACTION_OPERATIONS[(role, action)]
    except KeyError as exc:
        raise ValueError(f"unsupported worker role/action: {role}/{action}") from exc


def mapped_role_actions() -> frozenset[RoleAction]:
    return frozenset(_ACTION_OPERATIONS)
