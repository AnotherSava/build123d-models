import argparse
import sys

from .api import reconstruct


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='python -m sava.csg.build123d.reconstruct')
    parser.add_argument('mesh', help='Input mesh file (.off or .stl)')
    parser.add_argument('--out', help='Output Python file (default: stdout)')
    parser.add_argument('--sig-area-frac', type=float, default=0.005,
                        help='Minimum plane area as a fraction of total mesh surface area (default: 0.005 = 0.5%%). '
                             'Lower this to detect small features (cavities, fillets) that the default threshold drops; '
                             'raise it to ignore tessellation noise on dense meshes.')
    args = parser.parse_args(argv)

    result = reconstruct(args.mesh, sig_area_frac=args.sig_area_frac)
    if not result.is_2d5_extrudable:
        print(f'Reconstruction failed: {result.error}', file=sys.stderr)
        return 1

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(result.code)
    else:
        sys.stdout.reconfigure(encoding='utf-8')
        print(result.code)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
