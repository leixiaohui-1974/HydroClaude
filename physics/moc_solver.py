from typing import Tuple

class MOCSolver:
    """特征线法求解器"""

    @staticmethod
    def solve_canal_boundary(h_left: float, Q_left: float,
                            h_right: float, Q_right: float,
                            boundary, dx: float, dt: float,
                            area: float) -> Tuple[float, float]:
        """求解明渠内边界"""
        kwargs = {
            'h_upstream': h_left,
            'Q_upstream': Q_left,
            'h_downstream': h_right,
            'Q_downstream': Q_right,
            'dx': dx, 'dt': dt, 'area': area
        }
        return boundary.apply(None, **kwargs)

    @staticmethod
    def solve_pipe_boundary(H_left: float, Q_left: float,
                           H_right: float, Q_right: float,
                           boundary, wave_speed: float,
                           area: float) -> Tuple[float, float]:
        """求解管道内边界"""
        kwargs = {
            'H_upstream': H_left,
            'Q_upstream': Q_left,
            'H_downstream': H_right,
            'Q_downstream': Q_right,
            'wave_speed': wave_speed,
            'area': area
        }
        return boundary.apply(None, **kwargs)
