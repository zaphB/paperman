from .. import io

def main(args):
  authorList = [a.split() for a in ' '.join(
                  [args.separator if a == 'and' else a
                      for a in args.authors]).split(args.separator)]
  first = last = []
  if args.keep_first or args.keep_first_and_last:
    first = [authorList.pop(0)]
  if args.keep_last or args.keep_first_and_last:
    last = [authorList.pop(-1)]
  sortedAuthorList = sorted(authorList, key=lambda a: a[-1])
  authors = first+sortedAuthorList+last
  if not args.quiet:
    if any([len(a) != 2 for a in authors]):
      io.warn('there were names with more than one surname and one family name, '
              'they were treated as if all names except the last were surnames')
    if authorList == sortedAuthorList:
      io.info("list was properly sorted")
    else:
      io.info("list was _not_ properly sorted")
  if args.no_and:
    finalSep = args.separator.strip()+' '
  else:
    finalSep = ' and '
  def fmtAuthor(author, full=args.full_name):
    if full:
      return ' '.join([a.capitalize() for a in author])
    else:
      return (' '.join([a[0].upper()+'.' for a in author[:-1]])
                        +' '+author[-1].capitalize())
  io.info((args.separator.strip()+' ').join([fmtAuthor(a) for a in authors[:-1]])
            +finalSep+fmtAuthor(authors[-1]))
