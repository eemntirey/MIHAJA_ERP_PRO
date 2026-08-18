from app.tasks.backups import backup_database


def run_backup():
    result = backup_database('backups/erp-backup.zip')
    print(result)


if __name__ == '__main__':
    run_backup()
