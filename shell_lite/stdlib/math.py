from shell_lite.compiler.runtime_lib import *

__SHL_MODULES = {}


def main():

    def m_a40bca5d25f9_pow(base, exp):
        abs_exp = abs(exp)
        result = 1
        for i in range(0, abs_exp):
            result = result * base
        if exp < 0:
            return 1.0 / result
        else:
            return result

    def m_a40bca5d25f9_factorial(n):
        if n == 1:
            return 1
        return n * m_a40bca5d25f9_factorial(n - 1)

    def m_a40bca5d25f9_sqrt(n):
        if n == 0:
            return 0
        x = n / 2.0
        tolerance = 1e-05
        for i in range(0, 100):
            root_sqrt = x * x
            diff = abs(root_sqrt - n)
            if diff < tolerance:
                return x
            x = 0.5 * mixed_concat(x, n / x)
        return x

    def m_a40bca5d25f9_is_even(n):
        if n % 2 == 0:
            return True
        else:
            return False

    def m_a40bca5d25f9_is_odd(n):
        if n % 2 != 0:
            return True
        else:
            return False


if __name__ == "__main__":
    main()
