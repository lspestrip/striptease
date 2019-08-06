#pragma once

#include <QAbstractTableModel>
#include <QDateTime>
#include <QString>
#include <QVariantMap>

enum class CommandType {
    None,
    Command,
    Log,
    Tag,
};

struct Command {
    QDateTime time;
    CommandType type;
    QString url;
    QVariantMap parameters;
};

QString commandTypeToStr(CommandType type);
QString commandToStr(const Command & cmd);

class CommandList : public QAbstractTableModel
{
    Q_OBJECT

public:
    explicit CommandList(QObject *parent = nullptr);

    void loadFromJson(const QString & s);

    // Header:
    QVariant headerData(int section, Qt::Orientation orientation, int role = Qt::DisplayRole) const override;

    int rowCount(const QModelIndex &parent = QModelIndex()) const override;
    int columnCount(const QModelIndex &parent = QModelIndex()) const override;

    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const override;

    void setCommandTime(int index, const QDateTime & datetime) {
        command_list[index].time = datetime;

        emit dataChanged(
            createIndex(index, 0),
            createIndex(index, columnCount())
        );
    }
    QList<Command> command_list;
};

QDebug operator<<(QDebug debug, const Command &c);
